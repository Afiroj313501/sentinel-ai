"""Database access for AI fix suggestions."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ai.patch_service import FixProposal
from app.db.models import FindingRecord, FixSuggestionRecord


def get_fix(session: Session, finding_id: str) -> FixSuggestionRecord | None:
    return session.get(FixSuggestionRecord, finding_id)


def save_fix(
    session: Session,
    finding: FindingRecord,
    provider: str,
    model: str,
    proposal: FixProposal,
) -> FixSuggestionRecord:
    record = session.get(FixSuggestionRecord, finding.id) or FixSuggestionRecord(
        finding_id=finding.id,
        scan_id=finding.scan_id,
    )
    record.file_path = finding.file_path
    record.provider = provider
    record.model = model
    record.created_at = datetime.now(timezone.utc)
    record.can_fix = proposal.can_fix
    record.rationale = proposal.rationale
    record.diff = proposal.diff
    record.syntax_check = proposal.syntax_check
    session.add(record)
    session.commit()
    return record
