"""Scan orchestration for uploaded repositories."""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from pathlib import Path
from typing import BinaryIO

from app.core.config import get_settings
from app.scanners.base import Scanner, ScannerOutcome, build_outcome
from app.scanners.bandit_scanner import BanditScanner
from app.scanners.semgrep_scanner import SemgrepScanner
from app.schemas.finding import ScanResult
from app.schemas.scan import RepositoryMetadata
from app.services.normalization_service import count_by_severity, finalize_findings
from app.services.repository_service import ArchiveLimits, ingest_zip_workspace

logger = logging.getLogger(__name__)
NOTICE = "Findings come from the scanners listed in scanner_runs. An empty or short list does not prove the code is secure: scanners cover only specific rules and languages, and some may have been unavailable or failed."


def default_scanners() -> list[Scanner]:
    return [BanditScanner(), SemgrepScanner()]


def _run_scanner(scanner: Scanner, workspace: Path, scan_id: str, timeout: float) -> ScannerOutcome:
    started = time.monotonic()
    try:
        return scanner.scan(workspace, scan_id, timeout)
    except Exception:
        logger.exception("Scanner %s failed unexpectedly", scanner.name)
        return build_outcome(scanner.name, "failed", started, message="Scanner failed unexpectedly.")


def build_scan_result(metadata: RepositoryMetadata, outcomes: Sequence[ScannerOutcome]) -> ScanResult:
    findings = finalize_findings([f for outcome in outcomes for f in outcome.findings], metadata.scan_id)
    return ScanResult(metadata=metadata, scanner_runs=[o.run for o in outcomes], findings=findings,
                      severity_counts=count_by_severity(findings), notice=NOTICE)


def run_zip_scan(source: BinaryIO, filename: str, limits: ArchiveLimits | None = None,
                 scanners: Sequence[Scanner] | None = None) -> ScanResult:
    timeout = get_settings().scanner_timeout_seconds
    active = list(scanners) if scanners is not None else default_scanners()
    with ingest_zip_workspace(source, filename, limits) as repo:
        outcomes = [_run_scanner(scanner, repo.workspace, repo.metadata.scan_id, timeout) for scanner in active]
        return build_scan_result(repo.metadata, outcomes)
