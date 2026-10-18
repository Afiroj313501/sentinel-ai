"""Report building and rendering.

Everything that came from the scanned repository or an AI model is untrusted. The Markdown
renderer escapes it so it cannot inject HTML, links, headings, tables, or code fences.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.reports import explanations_for_scan, fixes_for_scan, list_scan_findings
from app.db.repository import get_scan
from app.schemas.explanation import ExplanationOut
from app.schemas.finding import SEVERITY_ORDER
from app.schemas.fix import FixSuggestionOut
from app.schemas.report import AI_REPORT_DISCLAIMER, Report, ReportFinding
from app.services.history_service import to_detail, to_finding
from app.services.scan_service import NOTICE

_MD_SPECIAL = re.compile(r"([\\`_{}\[\]()#+\-.!|~=:@])")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_WHITESPACE = re.compile(r"\s+")
_BACKTICK_RUN = re.compile(r"`+")

def build_report(session: Session, scan_id: str, include_ai: bool) -> Report | None:
    record = get_scan(session, scan_id)
    if record is None:
        return None

    explanations = explanations_for_scan(session, scan_id) if include_ai else {}
    fixes = fixes_for_scan(session, scan_id) if include_ai else {}

    findings: list[ReportFinding] = []
    for finding in list_scan_findings(session, scan_id):
        explanation = explanations.get(finding.id)
        fix = fixes.get(finding.id)
        findings.append(
            ReportFinding(
                **to_finding(finding).model_dump(),
                ai_explanation=(
                    ExplanationOut.model_validate(explanation, from_attributes=True)
                    if explanation
                    else None
                ),
                suggested_fix=(
                    FixSuggestionOut.model_validate(fix, from_attributes=True) if fix else None
                ),
            )
        )

    return Report(
        generated_at=datetime.now(timezone.utc),
        generator=f"Sentinel AI {get_settings().app_version}",
        scan=to_detail(record, NOTICE),
        findings=findings,
        ai_content_included=include_ai,
        ai_disclaimer=AI_REPORT_DISCLAIMER if include_ai else None,
    )

def render_json(report: Report) -> str:
    return report.model_dump_json(indent=2) + "\n"

# --- Markdown helpers -------------------------------------------------------

def md_text(value: object) -> str:
    """Escape untrusted text as single-line inline Markdown."""
    text = _WHITESPACE.sub(" ", _CONTROL.sub("", str(value))).strip()
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("*", "&#42;")
    return _MD_SPECIAL.sub(r"\\\1", text)

def md_code(value: object) -> str:
    """Untrusted text as an inline code span whose delimiters it cannot break out of."""
    text = _WHITESPACE.sub(" ", _CONTROL.sub("", str(value))).strip() or " "
    longest = max((len(run) for run in _BACKTICK_RUN.findall(text)), default=0)
    fence = "`" * (longest + 1)
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{pad}{text}{pad}{fence}"

def md_block(text: str, info: str = "") -> str:
    """Untrusted text as a fenced code block that its content cannot close early."""
    clean = _CONTROL.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
    longest = max((len(run) for run in _BACKTICK_RUN.findall(clean)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}{info}\n{clean}\n{fence}"

def md_quote(text: str) -> str:
    """Untrusted multi-line text as an escaped blockquote."""
    lines = [md_text(line) for line in str(text).splitlines()] or [""]
    return "\n".join(f"> {line}" if line else ">" for line in lines)

def _finding_lines(number: int, finding: ReportFinding) -> list[str]:
    span = (
        f"{finding.line_start}-{finding.line_end}"
        if finding.line_end > finding.line_start
        else str(finding.line_start)
    )
    cwe = f" Â· {md_text(finding.cwe)}" if finding.cwe else ""
    out = [
        f"### {number}. [{finding.severity.upper()}] {md_text(finding.title)}",
        "",
        f"- **Location:** {md_code(f'{finding.file_path}:{span}')}",
        f"- **Scanner:** {md_code(finding.scanner)} Â· rule {md_code(finding.rule_id)}",
        f"- **Confidence:** {finding.confidence}{cwe}",
        "",
        "**Scanner evidence**",
        "",
        md_quote(finding.evidence),
        "",
    ]
    if finding.snippet:
        out += ["**Code excerpt**", "", md_block(finding.snippet, "text"), ""]

    explanation = finding.ai_explanation
    if explanation:
        out += [
            "#### AI explanation (AI-generated, may be wrong)",
            "",
            f"_Written by {md_text(explanation.provider)} / {md_text(explanation.model)}; "
            f"AI confidence: {explanation.confidence}._",
            "",
        ]
        if not explanation.evidence_sufficient:
            out += [
                "> **Note:** the AI said the available evidence is not enough to judge this "
                "finding reliably.",
                "",
            ]
        out += [
            "**Summary**", "", md_quote(explanation.summary), "",
            "**Likely impact if it is a real issue**", "", md_quote(explanation.impact), "",
            "**Suggested remediation**", "", md_quote(explanation.remediation), "",
        ]

    fix = finding.suggested_fix
    if fix:
        out += ["#### AI-suggested fix (UNTESTED, review before use)", ""]
        if fix.can_fix and fix.diff:
            out += [md_quote(fix.rationale), "", md_block(fix.diff, "diff"), ""]
            if fix.syntax_check == "passed":
                out += ["_The patched excerpt parses as valid Python. This does not prove the fix works._", ""]
        else:
            out += ["The AI did not propose a patch.", "", md_quote(fix.rationale), ""]
        out += [md_quote(fix.notice), ""]
    return out

def render_markdown(report: Report) -> str:
    scan = report.scan
    meta = scan.metadata
    languages = ", ".join(f"{name} ({count})" for name, count in meta.languages.items()) or "none"

    out = [
        "# Sentinel AI security report",
        "",
        f"- **Archive:** {md_text(meta.archive_name)}",
        f"- **Scan ID:** {md_code(meta.scan_id)}",
        f"- **Scanned:** {scan.created_at.isoformat()}",
        f"- **Report generated:** {report.generated_at.isoformat()} by {md_text(report.generator)}",
        "",
        md_quote(scan.notice),
        "",
    ]
    if report.ai_disclaimer:
        out += [md_quote(report.ai_disclaimer), ""]

    out += ["## Summary", "", "| Severity | Findings |", "|---|---|"]
    out += [f"| {severity} | {scan.severity_counts[severity]} |" for severity in SEVERITY_ORDER]

    out += ["", "## Scanner coverage", "", "| Scanner | Status | Findings | Notes |", "|---|---|---|---|"]
    for run in scan.scanner_runs:
        name = md_text(run.scanner + (f" {run.version}" if run.version else ""))
        out.append(
            f"| {name} | {run.status.replace('_', ' ')} | {run.findings_count} | "
            f"{md_text(run.message or '')} |"
        )

    out += [
        "",
        "## Repository",
        "",
        f"- **Files scanned:** {meta.source_files}",
        f"- **Entries skipped:** {meta.skipped_entries}",
        f"- **Languages:** {md_text(languages)}",
    ]
    if meta.dependency_manifests:
        out.append("- **Dependency manifests:** " + ", ".join(md_code(m) for m in meta.dependency_manifests))

    out += ["", "## Findings", ""]
    if not report.findings:
        out.append(
            "No findings were reported by the scanners that ran. This does not prove the code is secure."
        )
    for number, finding in enumerate(report.findings, start=1):
        out += _finding_lines(number, finding)

    return "\n".join(out).rstrip() + "\n"
