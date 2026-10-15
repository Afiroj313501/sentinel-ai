"""Helpers for converting scanner output into safe, common findings."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from app.core.security import UnsafePathError, ensure_within
from app.schemas.finding import Finding, SEVERITY_ORDER

EVIDENCE_MAX_CHARS = 500


def normalize_severity(raw: object) -> str:
    return {
        "critical": "critical", "high": "high", "error": "high",
        "medium": "medium", "warning": "medium", "low": "low", "info": "info",
    }.get(str(raw).strip().lower(), "low")


def normalize_confidence(raw: object) -> str:
    value = str(raw).strip().lower()
    return value if value in {"high", "medium", "low"} else "unknown"


def truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit - 3] + "..."


def humanize(identifier: str) -> str:
    text = re.sub(r"[_-]+", " ", identifier).strip()
    return text[:1].upper() + text[1:]


def relative_posix_path(workspace: Path, reported: str) -> str | None:
    if not reported:
        return None
    candidate = Path(reported)
    if not candidate.is_absolute():
        candidate = workspace / candidate
    try:
        return candidate.resolve().relative_to(workspace.resolve()).as_posix()
    except (ValueError, OSError):
        return None


def read_snippet(workspace: Path, relative_path: str, line_start: int, line_end: int) -> str | None:
    try:
        target = ensure_within(workspace, workspace / relative_path)
        if not target.is_file():
            return None
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    except (UnsafePathError, OSError, ValueError):
        return None
    if not lines or line_start < 1 or line_start > len(lines):
        return None
    first = max(1, line_start - 2)
    last = min(len(lines), max(line_start, line_end) + 2)
    width = len(str(last))
    return truncate("\n".join(f"{n:>{width}} | {lines[n - 1]}" for n in range(first, last + 1)), 2000)


def finalize_findings(findings: list[Finding], scan_id: str) -> list[Finding]:
    unique: dict[tuple[str, str, str, int], Finding] = {}
    for finding in findings:
        unique.setdefault((finding.scanner, finding.rule_id, finding.file_path, finding.line_start), finding)
    ordered = sorted(unique.values(), key=lambda f: (SEVERITY_ORDER.index(f.severity), f.file_path, f.line_start))
    return [f.model_copy(update={"id": f"{scan_id[:12]}-{i:04d}"}) for i, f in enumerate(ordered, 1)]


def count_by_severity(findings: list[Finding]) -> dict[str, int]:
    counts = Counter(f.severity for f in findings)
    return {severity: counts.get(severity, 0) for severity in SEVERITY_ORDER}
