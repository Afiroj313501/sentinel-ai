"""Bulk queries used to assemble reports."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ExplanationRecord, FindingRecord, FixSuggestionRecord

def list_scan_findings(session: Session, scan_id: str) -> list[FindingRecord]:
    stmt = (
        select(FindingRecord)
        .where(FindingRecord.scan_id == scan_id)
        .order_by(FindingRecord.position)
    )
    return list(session.scalars(stmt))

def explanations_for_scan(session: Session, scan_id: str) -> dict[str, ExplanationRecord]:
    rows = session.scalars(select(ExplanationRecord).where(ExplanationRecord.scan_id == scan_id))
    return {row.finding_id: row for row in rows}

def fixes_for_scan(session: Session, scan_id: str) -> dict[str, FixSuggestionRecord]:
    rows = session.scalars(select(FixSuggestionRecord).where(FixSuggestionRecord.scan_id == scan_id))
    return {row.finding_id: row for row in rows}
