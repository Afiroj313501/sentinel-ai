"""Optional Semgrep JSON adapter using local rules."""

from __future__ import annotations

import json
import re
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from app.scanners.base import *
from app.schemas.finding import Finding
from app.services.normalization_service import *

RULES_FILE = Path(__file__).resolve().parent / "rules" / "semgrep-rules.yml"
SUPPORTED_SUFFIXES = frozenset({".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"})


@dataclass
class ParsedReport:
    findings: list[Finding]
    skipped_entries: int
    tool_errors: int
    truncated: bool


def _find_executable() -> str | None:
    return shutil.which("semgrep", path=str(Path(sys.executable).parent))


def _probe_version(executable: str, workspace: Path) -> str | None:
    try:
        result = run_tool([executable, "--version"], workspace, 30.0)
    except (ToolTimeoutError, ToolExecutionError):
        return None
    return result.stdout.strip().splitlines()[0].strip() if result.returncode == 0 and result.stdout.strip() else None


def _clean_rule_id(value: str) -> str:
    index = value.find("sentinel.")
    return value[index:] if index >= 0 else value


def _extract_cwe(metadata: dict) -> str | None:
    match = re.search(r"CWE-\d+", str(metadata.get("cwe", "")))
    return match.group(0) if match else None


def _entry_to_finding(entry: object, workspace: Path, scan_id: str) -> Finding | None:
    if not isinstance(entry, dict):
        return None
    try:
        path = relative_posix_path(workspace, str(entry["path"]))
        start, end = entry["start"], entry["end"]
        extra = entry["extra"]
        metadata = extra.get("metadata") or {}
        if path is None:
            return None
        line_start = int(start["line"])
        line_end = max(line_start, int(end["line"]))
        category = str(metadata.get("category", "security")).lower()
        return Finding(
            id="", scan_id=scan_id, scanner="semgrep", rule_id=_clean_rule_id(str(entry["check_id"])),
            title=humanize(_clean_rule_id(str(entry["check_id"]))),
            severity=normalize_severity(entry.get("severity")),
            confidence=normalize_confidence(metadata.get("confidence")),
            category=category if category in {"security", "bug", "quality"} else "security",
            file_path=path, line_start=line_start, line_end=line_end,
            evidence=truncate(str(extra.get("message", "")), EVIDENCE_MAX_CHARS),
            snippet=read_snippet(workspace, path, line_start, line_end),
            cwe=_extract_cwe(metadata),
        )
    except (KeyError, TypeError, ValueError, ValidationError):
        return None


def parse_semgrep_json(output: str, workspace: Path, scan_id: str) -> ParsedReport:
    try:
        report = json.loads(output)
    except json.JSONDecodeError as exc:
        raise ValueError from exc
    if not isinstance(report, dict) or not isinstance(report.get("results"), list):
        raise ValueError
    findings, skipped = [], 0
    for entry in report["results"][:MAX_FINDINGS_PER_SCANNER]:
        finding = _entry_to_finding(entry, workspace, scan_id)
        if finding is None:
            skipped += 1
        else:
            findings.append(finding)
    errors = report.get("errors") or []
    return ParsedReport(findings, skipped, len(errors) if isinstance(errors, list) else 0,
                        len(report["results"]) > MAX_FINDINGS_PER_SCANNER)


class SemgrepScanner:
    name = "semgrep"

    def scan(self, workspace: Path, scan_id: str, timeout: float) -> ScannerOutcome:
        started = time.monotonic()
        executable = _find_executable()
        if executable is None:
            return build_outcome(self.name, "unavailable", started, message="Semgrep is not installed in the backend environment.")
        version = _probe_version(executable, workspace)
        if version is None:
            return build_outcome(self.name, "unavailable", started, message="Semgrep is installed but cannot run in this environment.")
        if not has_files_with_suffix(workspace, SUPPORTED_SUFFIXES):
            return build_outcome(self.name, "skipped", started, version=version, message="No files supported by the Semgrep rule set.")
        args = [executable, "scan", "--config", str(RULES_FILE), "--json", "--metrics=off", "--disable-version-check", "--quiet", "."]
        try:
            result = run_tool(args, workspace, timeout)
        except ToolTimeoutError:
            return build_outcome(self.name, "timed_out", started, version=version, message=f"Semgrep exceeded the {timeout:g}-second limit.")
        except ToolExecutionError as exc:
            return build_outcome(self.name, "failed", started, version=version, message=f"Semgrep failed: {exc}.")
        if result.returncode != 0:
            return build_outcome(self.name, "failed", started, version=version, message=f"Semgrep exited with code {result.returncode}.")
        try:
            report = parse_semgrep_json(result.stdout, workspace, scan_id)
        except ValueError:
            return build_outcome(self.name, "failed", started, version=version, message="Semgrep produced output that could not be parsed.")
        message = describe_issues("Semgrep", report.skipped_entries, report.tool_errors, report.truncated)
        return build_outcome(self.name, "completed" if message is None else "partial", started, version=version, findings=report.findings, message=message)
