"""npm audit adapter for package lockfiles."""

from __future__ import annotations

import json
import logging
import re
import shutil
import time
from pathlib import Path

from pydantic import ValidationError

from app.scanners.base import (
    MAX_FINDINGS_PER_SCANNER,
    ScannerOutcome,
    ToolExecutionError,
    ToolTimeoutError,
    build_outcome,
    run_tool,
)
from app.schemas.finding import Finding
from app.services.normalization_service import (
    EVIDENCE_MAX_CHARS,
    normalize_severity,
    read_snippet,
    truncate,
)

logger = logging.getLogger(__name__)
MAX_LOCKFILES = 5
VERSION_TIMEOUT_SECONDS = 30.0
_NPM_SEVERITY = {"moderate": "medium"}


def _find_npm() -> str | None:
    return shutil.which("npm")


def _probe_version(npm: str, cwd: Path) -> str | None:
    try:
        result = run_tool([npm, "--version"], cwd, VERSION_TIMEOUT_SECONDS)
    except (ToolTimeoutError, ToolExecutionError):
        return None
    if result.returncode != 0:
        return None
    lines = result.stdout.strip().splitlines()
    return lines[0].strip() if lines else None


def _find_line(lines: list[str], node_path: str) -> int:
    needle = f'"{node_path}"'
    for number, text in enumerate(lines, start=1):
        if needle in text:
            return number
    return 1


def _fix_text(fix: object) -> str:
    if isinstance(fix, dict) and fix.get("name") and fix.get("version"):
        return f"Fix available: {fix['name']}@{fix['version']}."
    if fix is True:
        return "A fix is available via npm audit fix."
    return "No fix is available."


def _advisory_to_finding(
    package: str,
    info: dict,
    advisory: dict,
    lock_path: str,
    line: int,
    workspace: Path,
    scan_id: str,
) -> Finding | None:
    try:
        url = str(advisory.get("url") or "")
        rule_id = url.rstrip("/").rsplit("/", 1)[-1] if url else str(advisory["source"])
        title = str(advisory.get("title") or "Known vulnerability")
        raw_severity = str(advisory.get("severity") or info.get("severity") or "").lower()
        affected = advisory.get("range") or info.get("range") or "unknown versions"
        cwe = None
        cwes = advisory.get("cwe")
        if isinstance(cwes, list):
            for item in cwes:
                match = re.search(r"CWE-\d+", str(item))
                if match:
                    cwe = match.group(0)
                    break
        evidence = f"{package} ({affected}) is affected: {title}. {_fix_text(info.get('fixAvailable'))}"
        return Finding(
            id="",
            scan_id=scan_id,
            scanner="npm-audit",
            rule_id=rule_id,
            title=f"{title} ({package})",
            severity=normalize_severity(_NPM_SEVERITY.get(raw_severity, raw_severity)),
            confidence="high",
            category="security",
            file_path=lock_path,
            line_start=line,
            line_end=line,
            evidence=truncate(evidence, EVIDENCE_MAX_CHARS),
            snippet=read_snippet(workspace, lock_path, line, line),
            cwe=cwe,
        )
    except (KeyError, TypeError, ValueError, ValidationError):
        return None


def parse_npm_audit_json(
    stdout: str, lock_path: str, lock_lines: list[str], workspace: Path, scan_id: str
) -> tuple[list[Finding], int]:
    try:
        payload = json.loads(stdout)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("npm audit output is not valid JSON") from exc
    if not isinstance(payload, dict) or "error" in payload:
        raise ValueError("npm audit did not return a report")
    vulnerabilities = payload.get("vulnerabilities")
    if not isinstance(vulnerabilities, dict):
        raise ValueError("npm audit output has an unexpected structure")

    findings: list[Finding] = []
    dropped = 0
    for package, info in vulnerabilities.items():
        if not isinstance(info, dict) or not isinstance(info.get("via"), list):
            dropped += 1
            continue
        nodes = info.get("nodes")
        line = _find_line(lock_lines, str(nodes[0])) if isinstance(nodes, list) and nodes else 1
        for advisory in (item for item in info["via"] if isinstance(item, dict)):
            if len(findings) >= MAX_FINDINGS_PER_SCANNER:
                return findings, dropped
            finding = _advisory_to_finding(
                str(package), info, advisory, lock_path, line, workspace, scan_id
            )
            if finding is None:
                dropped += 1
            else:
                findings.append(finding)
    return findings, dropped


class NpmAuditScanner:
    name = "npm-audit"

    def scan(self, workspace: Path, scan_id: str, timeout: float) -> ScannerOutcome:
        started = time.monotonic()
        npm = _find_npm()
        if npm is None:
            return build_outcome(
                self.name, "unavailable", started,
                message="npm is not installed or not on PATH.",
            )
        version = _probe_version(npm, workspace)
        if version is None:
            return build_outcome(
                self.name, "unavailable", started,
                message="npm is installed but cannot run in this environment.",
            )
        locks = sorted(workspace.rglob("package-lock.json"))[:MAX_LOCKFILES]
        if not locks:
            return build_outcome(
                self.name, "skipped", started, version=version,
                message="No package-lock.json found (files over the size limit are not extracted).",
            )

        findings: list[Finding] = []
        audited = failed = unauditable = dropped = 0
        deadline = started + timeout
        for lock in locks:
            directory = lock.parent
            if not (directory / "package.json").is_file():
                unauditable += 1
                continue
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return build_outcome(
                    self.name, "timed_out", started, version=version, findings=findings,
                    message=f"npm audit exceeded the {timeout:g}-second limit.",
                )
            try:
                result = run_tool(
                    [npm, "audit", "--json", "--package-lock-only"], directory, remaining
                )
            except ToolTimeoutError:
                return build_outcome(
                    self.name, "timed_out", started, version=version, findings=findings,
                    message=f"npm audit exceeded the {timeout:g}-second limit.",
                )
            except ToolExecutionError:
                failed += 1
                continue
            relative = lock.relative_to(workspace).as_posix()
            try:
                lines = lock.read_text(encoding="utf-8", errors="replace").splitlines()
                lock_findings, lock_dropped = parse_npm_audit_json(
                    result.stdout, relative, lines, workspace, scan_id
                )
            except (ValueError, OSError):
                failed += 1
                continue
            audited += 1
            findings.extend(lock_findings)
            dropped += lock_dropped

        if audited == 0 and failed == 0:
            return build_outcome(
                self.name, "skipped", started, version=version,
                message="package-lock.json was found without a package.json beside it.",
            )
        if audited == 0:
            return build_outcome(
                self.name, "failed", started, version=version,
                message=(
                    f"npm audit could not complete for {failed} lockfile(s) "
                    "(often a network problem, since it queries an online service)."
                ),
            )
        parts: list[str] = []
        if failed:
            parts.append(f"npm audit could not complete for {failed} lockfile(s)")
        if unauditable:
            parts.append(f"{unauditable} lockfile(s) had no package.json beside them")
        if dropped:
            parts.append(f"{dropped} result(s) could not be processed and were dropped")
        message = "; ".join(parts) + "." if parts else None
        return build_outcome(
            self.name, "completed" if message is None else "partial", started,
            version=version, findings=findings, message=message,
        )
