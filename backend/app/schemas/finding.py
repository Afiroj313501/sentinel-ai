"""Schemas for normalized static-analysis findings."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.scan import RepositoryMetadata

Severity = Literal["critical", "high", "medium", "low", "info"]
Confidence = Literal["high", "medium", "low", "unknown"]
Category = Literal["security", "bug", "quality"]
ScannerStatus = Literal["completed", "partial", "skipped", "unavailable", "failed", "timed_out"]
SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")


class Finding(BaseModel):
    id: str
    scan_id: str
    scanner: str
    rule_id: str
    title: str
    severity: Severity
    confidence: Confidence
    category: Category
    file_path: str
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    evidence: str
    snippet: str | None = None
    cwe: str | None = None
    source: Literal["static-analysis"] = "static-analysis"


class ScannerRun(BaseModel):
    scanner: str
    status: ScannerStatus
    version: str | None = None
    findings_count: int = 0
    duration_seconds: float = 0.0
    message: str | None = None


class ScanResult(BaseModel):
    metadata: RepositoryMetadata
    scanner_runs: list[ScannerRun]
    findings: list[Finding]
    severity_counts: dict[str, int]
    notice: str
