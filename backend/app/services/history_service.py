"""Converters from database records to API schemas."""

from datetime import datetime, timezone

from app.db.models import FindingRecord, ScanRecord
from app.schemas.finding import Finding, ScannerRun
from app.schemas.history import ScanDetail, ScanSummary
from app.schemas.scan import RepositoryMetadata


def _aware(value: datetime) -> datetime:
    """SQLite returns naive datetimes; everything stored here is UTC."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def to_finding(record: FindingRecord) -> Finding:
    return Finding.model_validate(record, from_attributes=True)


def to_summary(record: ScanRecord) -> ScanSummary:
    return ScanSummary(
        scan_id=record.id,
        archive_name=record.archive_name,
        created_at=_aware(record.created_at),
        source_files=record.source_files,
        findings_total=record.findings_total,
        severity_counts=record.severity_counts,
        scanner_statuses={run["scanner"]: run["status"] for run in record.scanner_runs},
    )


def to_detail(record: ScanRecord, notice: str) -> ScanDetail:
    return ScanDetail(
        metadata=RepositoryMetadata(
            scan_id=record.id,
            archive_name=record.archive_name,
            source_files=record.source_files,
            skipped_entries=record.skipped_entries,
            total_bytes=record.total_bytes,
            languages=record.languages,
            dependency_manifests=record.dependency_manifests,
        ),
        created_at=_aware(record.created_at),
        scanner_runs=[ScannerRun(**run) for run in record.scanner_runs],
        severity_counts=record.severity_counts,
        findings_total=record.findings_total,
        notice=notice,
    )
