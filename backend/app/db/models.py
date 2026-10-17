"""SQLAlchemy models for persisted scans and findings."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ScanRecord(Base):
    __tablename__ = "scans"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    archive_name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source_files: Mapped[int]
    skipped_entries: Mapped[int]
    total_bytes: Mapped[int]
    languages: Mapped[dict] = mapped_column(JSON)
    dependency_manifests: Mapped[list] = mapped_column(JSON)
    scanner_runs: Mapped[list] = mapped_column(JSON)
    severity_counts: Mapped[dict] = mapped_column(JSON)
    findings_total: Mapped[int]

    findings: Mapped[list[FindingRecord]] = relationship(
        back_populates="scan", cascade="all, delete-orphan"
    )


class FindingRecord(Base):
    __tablename__ = "findings"
    __table_args__ = (Index("ix_findings_scan_position", "scan_id", "position"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    scan_id: Mapped[str] = mapped_column(ForeignKey("scans.id"), index=True)
    position: Mapped[int]
    scanner: Mapped[str] = mapped_column(String(40))
    rule_id: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(300))
    severity: Mapped[str] = mapped_column(String(10), index=True)
    confidence: Mapped[str] = mapped_column(String(10))
    category: Mapped[str] = mapped_column(String(10))
    file_path: Mapped[str] = mapped_column(String(500))
    line_start: Mapped[int]
    line_end: Mapped[int]
    evidence: Mapped[str] = mapped_column(Text)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    cwe: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source: Mapped[str] = mapped_column(String(30))

    scan: Mapped[ScanRecord] = relationship(back_populates="findings")
    explanation: Mapped[ExplanationRecord | None] = relationship(
        back_populates="finding", cascade="all, delete-orphan", uselist=False
    )


class ExplanationRecord(Base):
    """One AI explanation per finding, stored separately from scanner evidence."""

    __tablename__ = "explanations"

    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id"), primary_key=True)
    scan_id: Mapped[str] = mapped_column(String(32), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    summary: Mapped[str] = mapped_column(Text)
    impact: Mapped[str] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(10))
    remediation: Mapped[str] = mapped_column(Text)
    evidence_sufficient: Mapped[bool]

    finding: Mapped[FindingRecord] = relationship(back_populates="explanation")
