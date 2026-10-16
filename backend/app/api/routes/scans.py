"""Scan routes: create a scan from an upload, browse history, and query findings."""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, Response, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.repository import FindingFilters, delete_scan, get_scan, list_scans, query_findings, save_scan
from app.db.session import get_db
from app.schemas.finding import Category, ScanResult, Severity
from app.schemas.history import SCAN_ID_PATTERN, FindingsPage, ScanDetail, ScanListPage
from app.services.history_service import to_detail, to_finding, to_summary
from app.services.repository_service import ArchiveRejected
from app.services.scan_service import NOTICE, run_zip_scan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("/upload", response_model=ScanResult)
def upload_repository(
    file: UploadFile = File(...), session: Session = Depends(get_db)
) -> ScanResult:
    """Accept a ZIP archive, safely extract it, scan it, store it, and return findings."""
    try:
        result = run_zip_scan(file.file, file.filename or "")
    except ArchiveRejected as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    try:
        save_scan(session, result)
    except SQLAlchemyError:
        session.rollback()
        logger.exception("Could not save scan %s", result.metadata.scan_id)
        raise HTTPException(
            status_code=500, detail="The scan finished but its results could not be saved."
        )
    return result


@router.get("", response_model=ScanListPage)
def list_scan_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> ScanListPage:
    total, records = list_scans(session, limit, offset)
    return ScanListPage(
        total=total, limit=limit, offset=offset, items=[to_summary(record) for record in records]
    )


@router.get("/{scan_id}", response_model=ScanDetail)
def get_scan_detail(
    scan_id: str = Path(pattern=SCAN_ID_PATTERN), session: Session = Depends(get_db)
) -> ScanDetail:
    record = get_scan(session, scan_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Scan not found.")
    return to_detail(record, NOTICE)


@router.get("/{scan_id}/findings", response_model=FindingsPage)
def list_findings(
    scan_id: str = Path(pattern=SCAN_ID_PATTERN),
    severity: list[Severity] = Query(default=[], max_length=5),
    category: list[Category] = Query(default=[], max_length=3),
    scanner: list[str] = Query(default=[], max_length=10),
    q: str | None = Query(default=None, max_length=100),
    file_path: str | None = Query(default=None, max_length=300),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> FindingsPage:
    if get_scan(session, scan_id) is None:
        raise HTTPException(status_code=404, detail="Scan not found.")
    total, records = query_findings(
        session,
        scan_id,
        FindingFilters(
            severities=list(severity),
            categories=list(category),
            scanners=scanner,
            search=q,
            file_path=file_path,
        ),
        limit,
        offset,
    )
    return FindingsPage(
        total=total, limit=limit, offset=offset, items=[to_finding(record) for record in records]
    )


@router.delete("/{scan_id}", status_code=204)
def remove_scan(
    scan_id: str = Path(pattern=SCAN_ID_PATTERN), session: Session = Depends(get_db)
) -> Response:
    if not delete_scan(session, scan_id):
        raise HTTPException(status_code=404, detail="Scan not found.")
    return Response(status_code=204)
