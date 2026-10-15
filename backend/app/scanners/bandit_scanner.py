"""Bandit JSON adapter."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from app.scanners.base import *
from app.schemas.finding import Finding
from app.services.normalization_service import *

PYTHON_SUFFIXES = frozenset({".py"})


@dataclass
class ParsedReport:
    findings: list[Finding]
    skipped_entries: int
    tool_errors: int
    truncated: bool


def _bandit_installed() -> bool:
    return importlib.util.find_spec("bandit") is not None


def _installed_version() -> str | None:
    try:
        return importlib.metadata.version("bandit")
    except importlib.metadata.PackageNotFoundError:
        return None


def _entry_to_finding(entry: object, workspace: Path, scan_id: str) -> Finding | None:
    if not isinstance(entry, dict):
        return None
    try:
        path = relative_posix_path(workspace, str(entry["filename"]))
        line_start = int(entry["line_number"])
        if path is None or line_start < 1:
            return None
        line_end = max(line_start, *(int(n) for n in (entry.get("line_range") or [line_start])))
        cwe = entry.get("issue_cwe")
        cwe_id = f"CWE-{int(cwe['id'])}" if isinstance(cwe, dict) and cwe.get("id") else None
        return Finding(
            id="", scan_id=scan_id, scanner="bandit", rule_id=str(entry["test_id"]),
            title=humanize(str(entry.get("test_name") or entry["test_id"])),
            severity=normalize_severity(entry.get("issue_severity")),
            confidence=normalize_confidence(entry.get("issue_confidence")), category="security",
            file_path=path, line_start=line_start, line_end=line_end,
            evidence=truncate(str(entry.get("issue_text", "")), EVIDENCE_MAX_CHARS),
            snippet=read_snippet(workspace, path, line_start, line_end), cwe=cwe_id,
        )
    except (KeyError, TypeError, ValueError, ValidationError):
        return None


def parse_bandit_json(output: str, workspace: Path, scan_id: str) -> ParsedReport:
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
    return ParsedReport(findings, skipped, len(report.get("errors") or []), len(report["results"]) > MAX_FINDINGS_PER_SCANNER)


class BanditScanner:
    name = "bandit"

    def scan(self, workspace: Path, scan_id: str, timeout: float) -> ScannerOutcome:
        started = time.monotonic()
        if not _bandit_installed():
            return build_outcome(self.name, "unavailable", started, message="Bandit is not installed in the backend environment.")
        version = _installed_version()
        if not has_files_with_suffix(workspace, PYTHON_SUFFIXES):
            return build_outcome(self.name, "skipped", started, version=version, message="No Python files to analyze.")
        try:
            result = run_tool([sys.executable, "-m", "bandit", "-r", ".", "-f", "json", "-q", "--exit-zero"], workspace, timeout)
        except ToolTimeoutError:
            return build_outcome(self.name, "timed_out", started, version=version, message=f"Bandit exceeded the {timeout:g}-second limit.")
        except ToolExecutionError as exc:
            return build_outcome(self.name, "failed", started, version=version, message=f"Bandit failed: {exc}.")
        if result.returncode != 0:
            return build_outcome(self.name, "failed", started, version=version, message=f"Bandit exited with code {result.returncode}.")
        try:
            report = parse_bandit_json(result.stdout, workspace, scan_id)
        except ValueError:
            return build_outcome(self.name, "failed", started, version=version, message="Bandit produced output that could not be parsed.")
        message = describe_issues("Bandit", report.skipped_entries, report.tool_errors, report.truncated)
        return build_outcome(self.name, "completed" if message is None else "partial", started, version=version, findings=report.findings, message=message)
