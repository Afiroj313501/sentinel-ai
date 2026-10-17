"""Persistence helpers for explanations, separate from scanner findings."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import ExplanationRecord, FindingRecord
from app.schemas.explanation import Explanation


def get_explanation(session: Session, finding_id: str) -> ExplanationRecord | None:
    return session.get(ExplanationRecord, finding_id)


def save_explanation(
    session: Session,
    finding: FindingRecord,
    provider: str,
    model: str,
    explanation: Explanation,
) -> ExplanationRecord:
    record = session.get(ExplanationRecord, finding.id)
    if record is None:
        record = ExplanationRecord(finding_id=finding.id, scan_id=finding.scan_id)
        session.add(record)
    record.provider = provider
    record.model = model
    record.created_at = datetime.now(timezone.utc)
    record.summary = explanation.summary
    record.impact = explanation.impact
    record.confidence = explanation.confidence
    record.remediation = explanation.remediation
    record.evidence_sufficient = explanation.evidence_sufficient
    session.commit()
    session.refresh(record)
    return record
