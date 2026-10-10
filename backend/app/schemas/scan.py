"""Schemas for scan requests and repository metadata."""

from pydantic import BaseModel


class RepositoryMetadata(BaseModel):
    scan_id: str
    archive_name: str
    source_files: int
    skipped_entries: int
    total_bytes: int
    languages: dict[str, int]
    dependency_manifests: list[str]
