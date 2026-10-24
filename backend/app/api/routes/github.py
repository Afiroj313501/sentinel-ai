"""Scan a public GitHub repository by URL."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_optional_user
from app.db.models import UserRecord
from app.db.repository import save_scan
from app.db.session import get_db
from app.schemas.finding import ScanResult
from app.services.github_service import run_github_scan
from app.services.repository_service import ArchiveRejected
from app.services.scan_service import ScanBusy

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scans", tags=["scans"])


class GithubScanRequest(BaseModel):
    url: str = Field(min_length=1, max_length=300)


@router.post("/github", response_model=ScanResult)
def scan_github_repository(
    body: GithubScanRequest,
    session: Session = Depends(get_db),
    current_user: UserRecord | None = Depends(get_optional_user),
) -> ScanResult:
    try:
        result = run_github_scan(body.url)
    except ScanBusy as exc:
        raise HTTPException(
            status_code=429,
            detail="The server is busy with other scans. Try again shortly.",
            headers={"Retry-After": "15"},
        ) from exc
    except ArchiveRejected as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    try:
        save_scan(session, result, user_id=current_user.id if current_user else None)
    except SQLAlchemyError:
        session.rollback()
        logger.exception("Could not save scan %s", result.metadata.scan_id)
        raise HTTPException(
            status_code=500, detail="The scan finished but its results could not be saved."
        )
    return result
