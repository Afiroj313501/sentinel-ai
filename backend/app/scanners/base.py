"""Shared process and result helpers for scanner adapters."""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from app.schemas.finding import Finding, ScannerRun, ScannerStatus

MAX_OUTPUT_CHARS = 10 * 1024 * 1024
MAX_FINDINGS_PER_SCANNER = 1000


class ToolTimeoutError(Exception):
    pass


class ToolExecutionError(Exception):
    pass


@dataclass(frozen=True)
class ToolResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass
class ScannerOutcome:
    run: ScannerRun
    findings: list[Finding] = field(default_factory=list)


class Scanner(Protocol):
    name: str

    def scan(self, workspace: Path, scan_id: str, timeout: float) -> ScannerOutcome: ...


def safe_env() -> dict[str, str]:
    allowed = ("PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "USERPROFILE", "LOCALAPPDATA", "APPDATA")
    env = {key: os.environ[key] for key in allowed if key in os.environ}
    env.update({"PYTHONUTF8": "1", "SEMGREP_SEND_METRICS": "off", "SEMGREP_ENABLE_VERSION_CHECK": "0"})
    return env


def run_tool(args: list[str], cwd: Path, timeout: float) -> ToolResult:
    try:
        completed = subprocess.run(
            args, cwd=cwd, env=safe_env(), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, check=False, shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolTimeoutError from exc
    except OSError as exc:
        raise ToolExecutionError("the tool could not be started") from exc
    stdout = completed.stdout or ""
    if len(stdout) > MAX_OUTPUT_CHARS:
        raise ToolExecutionError("the tool output was too large")
    return ToolResult(completed.returncode, stdout, completed.stderr or "")


def has_files_with_suffix(workspace: Path, suffixes: frozenset[str]) -> bool:
    return any(p.is_file() and p.suffix.lower() in suffixes for p in workspace.rglob("*"))


def build_outcome(scanner: str, status: ScannerStatus, started: float, *, version: str | None = None,
                  findings: list[Finding] | None = None, message: str | None = None) -> ScannerOutcome:
    findings = findings or []
    return ScannerOutcome(
        run=ScannerRun(scanner=scanner, status=status, version=version, findings_count=len(findings),
                       duration_seconds=round(time.monotonic() - started, 2), message=message),
        findings=findings,
    )


def describe_issues(tool: str, skipped: int, errors: int, truncated: bool) -> str | None:
    parts = []
    if errors:
        parts.append(f"{tool} reported {errors} file-level error(s)")
    if skipped:
        parts.append(f"{skipped} result(s) could not be processed and were dropped")
    if truncated:
        parts.append(f"results were capped at {MAX_FINDINGS_PER_SCANNER} findings")
    return "; ".join(parts) + "." if parts else None
