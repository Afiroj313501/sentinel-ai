"""Scan routes."""

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.scan import RepositoryMetadata
from app.services.repository_service import ArchiveRejected, ingest_zip_upload

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("/upload", response_model=RepositoryMetadata)
def upload_repository(file: UploadFile = File(...)) -> RepositoryMetadata:
    """Accept a ZIP archive, validate and extract it safely, return its metadata."""
    try:
        return ingest_zip_upload(file.file, file.filename or "")
    except ArchiveRejected as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
