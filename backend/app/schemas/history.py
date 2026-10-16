"""Response schemas for scan history and findings queries."""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.finding import Finding, ScannerRun
from app.schemas.scan import RepositoryMetadata

SCAN_ID_PATTERN = r"^[0-9a-f]{32}$"
FINDING_ID_PATTERN = r"^[0-9a-f]{12}-\d{4,}$"


class ScanSummary(BaseModel):
    scan_id: str
    archive_name: str
    created_at: datetime
    source_files: int
    findings_total: int
    severity_counts: dict[str, int]
    scanner_statuses: dict[str, str]


class ScanListPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ScanSummary]


class ScanDetail(BaseModel):
    metadata: RepositoryMetadata
    created_at: datetime
    scanner_runs: list[ScannerRun]
    severity_counts: dict[str, int]
    findings_total: int
    notice: str


class FindingsPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[Finding]
