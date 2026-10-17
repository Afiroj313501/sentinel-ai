"""Finding routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.explanation_service import InvalidModelOutput, generate_explanation
from app.ai.provider import AIProviderError, AIProviderUnavailable, get_provider
from app.db.explanation_repository import get_explanation, save_explanation
from app.db.repository import get_finding
from app.db.session import get_db
from app.schemas.explanation import ExplanationOut
from app.schemas.finding import Finding
from app.schemas.history import FINDING_ID_PATTERN
from app.services.history_service import to_finding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/findings", tags=["findings"])
provider_dependency = get_provider


def _explanation_response(record) -> ExplanationOut:
    return ExplanationOut.model_validate(record, from_attributes=True)


@router.post("/{finding_id}/explain", response_model=ExplanationOut)
def explain_finding(
    finding_id: str = Path(pattern=FINDING_ID_PATTERN),
    refresh: bool = Query(default=False),
    session: Session = Depends(get_db),
    provider=Depends(provider_dependency),
) -> ExplanationOut:
    finding = get_finding(session, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found.")
    if not refresh:
        cached = get_explanation(session, finding_id)
        if cached is not None:
            return _explanation_response(cached)

    try:
        explanation = generate_explanation(provider, to_finding(finding))
    except AIProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc
    except AIProviderError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc
    except InvalidModelOutput as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    try:
        saved = save_explanation(session, finding, provider.name, provider.model, explanation)
    except SQLAlchemyError:
        session.rollback()
        logger.exception("Could not save explanation for finding %s", finding_id)
        raise HTTPException(
            status_code=500, detail="The explanation was generated but could not be saved."
        )
    return _explanation_response(saved)


@router.get("/{finding_id}/explanation", response_model=ExplanationOut)
def get_finding_explanation(
    finding_id: str = Path(pattern=FINDING_ID_PATTERN), session: Session = Depends(get_db)
) -> ExplanationOut:
    if get_finding(session, finding_id) is None:
        raise HTTPException(status_code=404, detail="Finding not found.")
    record = get_explanation(session, finding_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Explanation not found.")
    return _explanation_response(record)


@router.get("/{finding_id}", response_model=Finding)
def get_finding_detail(
    finding_id: str = Path(pattern=FINDING_ID_PATTERN), session: Session = Depends(get_db)
) -> Finding:
    record = get_finding(session, finding_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Finding not found.")
    return to_finding(record)
