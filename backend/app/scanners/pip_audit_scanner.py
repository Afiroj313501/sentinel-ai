"""pip-audit adapter for exact Python dependency pins."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import logging
import re
import sys
import tempfile
import time
from dataclasses import dataclass, field
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
from app.services.normalization_service import EVIDENCE_MAX_CHARS, read_snippet, truncate

logger = logging.getLogger(__name__)

MAX_REQUIREMENT_FILES = 20
MAX_PINNED_PACKAGES = 200
_PIN = re.compile(
    r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*==\s*"
    r"([A-Za-z0-9][A-Za-z0-9.!+_-]*)$"
)


def _canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


@dataclass(frozen=True)
class Pin:
    name: str
    version: str
    file_path: str
    line: int


@dataclass
class PinCollection:
    pins: list[Pin] = field(default_factory=list)
    unpinned: int = 0
    files: int = 0
    truncated: bool = False


@dataclass
class AuditReport:
    findings: list[Finding] = field(default_factory=list)
    unaudited: int = 0
    skipped: int = 0
    truncated: bool = False


def parse_requirements(text: str, file_path: str) -> PinCollection:
    result = PinCollection()
    for number, raw in enumerate(text.splitlines(), start=1):
        line = re.split(r"\s+#", raw.strip(), maxsplit=1)[0].strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        line = line.rstrip("\\").split(";", 1)[0].strip()
        match = _PIN.match(line)
        if match:
            result.pins.append(Pin(match.group(1), match.group(2), file_path, number))
        else:
            result.unpinned += 1
    return result


def collect_pins(workspace: Path) -> PinCollection:
    collection = PinCollection()
    seen: set[tuple[str, str]] = set()
    for path in sorted(workspace.rglob("requirements.txt"))[:MAX_REQUIREMENT_FILES]:
        if not path.is_file():
            continue
        collection.files += 1
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        parsed = parse_requirements(text, path.relative_to(workspace).as_posix())
        collection.unpinned += parsed.unpinned
        for pin in parsed.pins:
            key = (_canonical(pin.name), pin.version)
            if key in seen:
                continue
            if len(collection.pins) >= MAX_PINNED_PACKAGES:
                collection.truncated = True
                continue
            seen.add(key)
            collection.pins.append(pin)
    return collection


def _vuln_to_finding(pin: Pin, vuln: object, workspace: Path, scan_id: str) -> Finding | None:
    if not isinstance(vuln, dict):
        return None
    try:
        vuln_id = str(vuln["id"])
        fixes = vuln.get("fix_versions") or []
        fix_text = (
            f"Fixed in: {', '.join(str(fix) for fix in fixes)}."
            if fixes
            else "No fixed version is listed."
        )
        description = str(vuln.get("description") or "").strip()
        evidence = (
            f"{pin.name}=={pin.version} is affected by {vuln_id}. {fix_text} "
            f"(pip-audit does not report severity; medium is a default.) {description}"
        )
        return Finding(
            id="",
            scan_id=scan_id,
            scanner="pip-audit",
            rule_id=vuln_id,
            title=f"Vulnerable dependency: {pin.name} {pin.version}",
            severity="medium",
            confidence="high",
            category="security",
            file_path=pin.file_path,
            line_start=pin.line,
            line_end=pin.line,
            evidence=truncate(evidence.strip(), EVIDENCE_MAX_CHARS),
            snippet=read_snippet(workspace, pin.file_path, pin.line, pin.line),
        )
    except (KeyError, TypeError, ValueError, ValidationError):
        return None


def parse_pip_audit_json(
    stdout: str, pins: list[Pin], workspace: Path, scan_id: str
) -> AuditReport:
    try:
        payload = json.loads(stdout)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("pip-audit output is not valid JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("dependencies"), list):
        raise ValueError("pip-audit output has an unexpected structure")

    index = {(_canonical(pin.name), pin.version): pin for pin in pins}
    report = AuditReport()
    for dependency in payload["dependencies"]:
        if not isinstance(dependency, dict):
            report.skipped += 1
            continue
        if dependency.get("skip_reason"):
            report.unaudited += 1
            continue
        vulnerabilities = dependency.get("vulns")
        if not vulnerabilities:
            continue
        if not isinstance(vulnerabilities, list):
            report.skipped += 1
            continue
        pin = index.get(
            (_canonical(str(dependency.get("name", ""))), str(dependency.get("version", "")))
        )
        for vulnerability in vulnerabilities:
            if len(report.findings) >= MAX_FINDINGS_PER_SCANNER:
                report.truncated = True
                break
            finding = (
                None
                if pin is None
                else _vuln_to_finding(pin, vulnerability, workspace, scan_id)
            )
            if finding is None:
                report.skipped += 1
            else:
                report.findings.append(finding)
    return report


def _pip_audit_installed() -> bool:
    return importlib.util.find_spec("pip_audit") is not None


def _installed_version() -> str | None:
    try:
        return importlib.metadata.version("pip-audit")
    except importlib.metadata.PackageNotFoundError:
        return None


def _coverage_message(collection: PinCollection, report: AuditReport) -> str | None:
    parts: list[str] = []
    if report.unaudited:
        parts.append(
            f"{report.unaudited} package(s) could not be audited by the vulnerability service"
        )
    if collection.unpinned:
        parts.append(
            f"{collection.unpinned} requirement(s) were not checked because they are not "
            "pinned to an exact version"
        )
    if report.skipped:
        parts.append(f"{report.skipped} result(s) could not be processed and were dropped")
    if collection.truncated:
        parts.append(f"only the first {MAX_PINNED_PACKAGES} pinned packages were audited")
    if report.truncated:
        parts.append(f"results were capped at {MAX_FINDINGS_PER_SCANNER} findings")
    return "; ".join(parts) + "." if parts else None


class PipAuditScanner:
    name = "pip-audit"

    def scan(self, workspace: Path, scan_id: str, timeout: float) -> ScannerOutcome:
        started = time.monotonic()
        if not _pip_audit_installed():
            return build_outcome(
                self.name,
                "unavailable",
                started,
                message="pip-audit is not installed in the backend environment.",
            )
        version = _installed_version()
        collection = collect_pins(workspace)
        if collection.files == 0:
            return build_outcome(
                self.name, "skipped", started, version=version,
                message="No requirements.txt found.",
            )
        if not collection.pins:
            return build_outcome(
                self.name, "skipped", started, version=version,
                message=(
                    "No pinned (name==version) requirements to audit; "
                    f"{collection.unpinned} unpinned requirement(s) were not checked."
                ),
            )

        with tempfile.TemporaryDirectory(prefix="sentinel_audit_") as temp_dir:
            requirements = Path(temp_dir) / "requirements.txt"
            requirements.write_text(
                "".join(f"{pin.name}=={pin.version}\n" for pin in collection.pins),
                encoding="utf-8",
            )
            args = [
                sys.executable, "-m", "pip_audit", "--disable-pip", "--no-deps",
                "-r", str(requirements), "-f", "json", "--progress-spinner", "off",
            ]
            try:
                result = run_tool(args, workspace, timeout)
            except ToolTimeoutError:
                return build_outcome(
                    self.name, "timed_out", started, version=version,
                    message=f"pip-audit exceeded the {timeout:g}-second limit.",
                )
            except ToolExecutionError as exc:
                return build_outcome(
                    self.name, "failed", started, version=version,
                    message=f"pip-audit failed: {exc}.",
                )

        if result.returncode not in (0, 1):
            logger.warning("pip-audit exited with code %s", result.returncode)
            return build_outcome(
                self.name, "failed", started, version=version,
                message=(
                    f"pip-audit exited with code {result.returncode} "
                    "(often a network problem, since it queries an online service)."
                ),
            )
        try:
            report = parse_pip_audit_json(result.stdout, collection.pins, workspace, scan_id)
        except ValueError:
            return build_outcome(
                self.name, "failed", started, version=version,
                message="pip-audit produced output that could not be parsed.",
            )

        message = _coverage_message(collection, report)
        return build_outcome(
            self.name, "completed" if message is None else "partial", started,
            version=version, findings=report.findings, message=message,
        )
