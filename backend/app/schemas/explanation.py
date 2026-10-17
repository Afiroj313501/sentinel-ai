"""Schemas for validated AI explanations."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

AI_NOTICE = (
    "AI-generated explanation. It can be wrong or incomplete. The scanner evidence "
    "is shown separately and is the source of truth."
)


class Explanation(BaseModel):
    summary: str = Field(min_length=1, max_length=600)
    impact: str = Field(min_length=1, max_length=1200)
    confidence: Literal["high", "medium", "low"]
    remediation: str = Field(min_length=1, max_length=1200)
    evidence_sufficient: bool


class ExplanationOut(Explanation):
    finding_id: str
    provider: str
    model: str
    created_at: datetime
    notice: str = AI_NOTICE

    @field_validator("created_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
