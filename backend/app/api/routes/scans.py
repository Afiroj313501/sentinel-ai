"""Scan routes."""

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.finding import ScanResult
from app.services.repository_service import ArchiveRejected
from app.services.scan_service import run_zip_scan

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("/upload", response_model=ScanResult)
def upload_repository(file: UploadFile = File(...)) -> ScanResult:
    """Accept a ZIP archive, safely extract it, scan it, and return findings."""
    try:
        return run_zip_scan(file.file, file.filename or "")
    except ArchiveRejected as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
