"""Database access for scans and findings."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import FindingRecord, ScanRecord
from app.schemas.finding import ScanResult


@dataclass
class FindingFilters:
    severities: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    scanners: list[str] = field(default_factory=list)
    search: str | None = None
    file_path: str | None = None


def save_scan(session: Session, result: ScanResult) -> None:
    """Store a completed scan and its findings in one transaction."""
    metadata = result.metadata
    record = ScanRecord(
        id=metadata.scan_id,
        archive_name=metadata.archive_name,
        created_at=datetime.now(timezone.utc),
        source_files=metadata.source_files,
        skipped_entries=metadata.skipped_entries,
        total_bytes=metadata.total_bytes,
        languages=metadata.languages,
        dependency_manifests=metadata.dependency_manifests,
        scanner_runs=[run.model_dump() for run in result.scanner_runs],
        severity_counts=result.severity_counts,
        findings_total=len(result.findings),
        findings=[
            FindingRecord(position=position, **finding.model_dump())
            for position, finding in enumerate(result.findings)
        ],
    )
    session.add(record)
    session.commit()


def list_scans(session: Session, limit: int, offset: int) -> tuple[int, list[ScanRecord]]:
    total = session.scalar(select(func.count()).select_from(ScanRecord)) or 0
    rows = session.scalars(
        select(ScanRecord).order_by(ScanRecord.created_at.desc()).limit(limit).offset(offset)
    ).all()
    return total, list(rows)


def get_scan(session: Session, scan_id: str) -> ScanRecord | None:
    return session.get(ScanRecord, scan_id)


def delete_scan(session: Session, scan_id: str) -> bool:
    record = session.get(ScanRecord, scan_id)
    if record is None:
        return False
    session.delete(record)
    session.commit()
    return True


def get_finding(session: Session, finding_id: str) -> FindingRecord | None:
    return session.get(FindingRecord, finding_id)


def query_findings(
    session: Session, scan_id: str, filters: FindingFilters, limit: int, offset: int
) -> tuple[int, list[FindingRecord]]:
    stmt = select(FindingRecord).where(FindingRecord.scan_id == scan_id)
    if filters.severities:
        stmt = stmt.where(FindingRecord.severity.in_(filters.severities))
    if filters.categories:
        stmt = stmt.where(FindingRecord.category.in_(filters.categories))
    if filters.scanners:
        stmt = stmt.where(FindingRecord.scanner.in_(filters.scanners))
    if filters.search:
        stmt = stmt.where(
            or_(
                FindingRecord.title.contains(filters.search, autoescape=True),
                FindingRecord.evidence.contains(filters.search, autoescape=True),
                FindingRecord.rule_id.contains(filters.search, autoescape=True),
            )
        )
    if filters.file_path:
        stmt = stmt.where(FindingRecord.file_path.contains(filters.file_path, autoescape=True))

    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = session.scalars(stmt.order_by(FindingRecord.position).limit(limit).offset(offset)).all()
    return total, list(rows)
