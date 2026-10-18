"""Schemas for downloadable scan reports."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.explanation import ExplanationOut
from app.schemas.finding import Finding
from app.schemas.fix import FixSuggestionOut
from app.schemas.history import ScanDetail

AI_REPORT_DISCLAIMER = (
    "AI-generated sections are labeled as such. They can be wrong or incomplete, and suggested "
    "patches are untested. Scanner evidence is the source of truth."
)

class ReportFinding(Finding):
    """A scanner finding, with optional AI material kept in clearly separate fields."""

    ai_explanation: ExplanationOut | None = None
    suggested_fix: FixSuggestionOut | None = None

class Report(BaseModel):
    report_version: Literal[1] = 1
    generated_at: datetime
    generator: str
    scan: ScanDetail
    findings: list[ReportFinding]
    ai_content_included: bool
    ai_disclaimer: str | None = None
