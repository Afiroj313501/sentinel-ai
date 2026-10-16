"""Finding routes."""

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.db.repository import get_finding
from app.db.session import get_db
from app.schemas.finding import Finding
from app.schemas.history import FINDING_ID_PATTERN
from app.services.history_service import to_finding

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("/{finding_id}", response_model=Finding)
def get_finding_detail(
    finding_id: str = Path(pattern=FINDING_ID_PATTERN), session: Session = Depends(get_db)
) -> Finding:
    record = get_finding(session, finding_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Finding not found.")
    return to_finding(record)
