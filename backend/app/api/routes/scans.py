"""Scan routes: create a scan from an upload, browse history, query findings, export reports."""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, Response, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.repository import (
    FindingFilters,
    delete_scan,
    get_scan,
    list_scans,
    query_findings,
    save_scan,
)
from app.db.session import get_db
from app.schemas.finding import Category, ScanResult, Severity
from app.schemas.history import SCAN_ID_PATTERN, FindingsPage, ScanDetail, ScanListPage
from app.services.history_service import to_detail, to_finding, to_summary
from app.services.report_service import build_report, render_json, render_markdown
from app.services.repository_service import ArchiveRejected
from app.services.scan_service import NOTICE, ScanBusy, run_zip_scan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scans", tags=["scans"])

@router.post("/upload", response_model=ScanResult)
def upload_repository(
    file: UploadFile = File(...), session: Session = Depends(get_db)
) -> ScanResult:
    """Accept a ZIP archive, validate and extract it safely, scan it, store and return results."""
    try:
        result = run_zip_scan(file.file, file.filename or "")
    except ScanBusy as exc:
        raise HTTPException(
            status_code=429,
            detail="The server is busy with other scans. Try again shortly.",
            headers={"Retry-After": "15"},
        ) from exc
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
        total=total, limit=limit, offset=offset, items=[to_summary(r) for r in records]
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
    filters = FindingFilters(
        severities=list(severity),
        categories=list(category),
        scanners=scanner,
        search=q,
        file_path=file_path,
    )
    total, records = query_findings(session, scan_id, filters, limit, offset)
    return FindingsPage(
        total=total, limit=limit, offset=offset, items=[to_finding(r) for r in records]
    )

@router.get("/{scan_id}/report")
def download_report(
    scan_id: str = Path(pattern=SCAN_ID_PATTERN),
    report_format: Literal["json", "markdown"] = Query(default="json", alias="format"),
    include_ai: bool = Query(default=False),
    session: Session = Depends(get_db),
) -> Response:
    """Download a report. Scanner evidence comes first; AI content is opt-in and labeled."""
    report = build_report(session, scan_id, include_ai)
    if report is None:
        raise HTTPException(status_code=404, detail="Scan not found.")

    if report_format == "markdown":
        body, media_type, extension = render_markdown(report), "text/markdown; charset=utf-8", "md"
    else:
        body, media_type, extension = render_json(report), "application/json", "json"

    filename = f"sentinel-report-{scan_id[:8]}.{extension}"
    return Response(
        content=body,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )

@router.delete("/{scan_id}", status_code=204)
def remove_scan(
    scan_id: str = Path(pattern=SCAN_ID_PATTERN), session: Session = Depends(get_db)
) -> Response:
    if not delete_scan(session, scan_id):
        raise HTTPException(status_code=404, detail="Scan not found.")
    return Response(status_code=204)
