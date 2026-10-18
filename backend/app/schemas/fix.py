"""Schemas for AI-proposed patches. Suggestions are never applied automatically."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, field_validator

FIX_NOTICE = (
    "AI-generated suggestion. It is untested: it has not been applied, compiled, or run. "
    "It was written from a short code excerpt, so review it carefully and test it yourself. "
    "Sentinel never applies patches automatically."
)


class FixSuggestionOut(BaseModel):
    finding_id: str
    file_path: str
    can_fix: bool
    rationale: str
    diff: str | None
    syntax_check: Literal["passed", "not_checked"]
    provider: str
    model: str
    created_at: datetime
    tested: Literal[False] = False
    requires_human_review: Literal[True] = True
    notice: str = FIX_NOTICE

    @field_validator("created_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
