"""Fix suggestion routes. Suggestions are text for human review; nothing is applied."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.patch_service import NoSourceExcerpt, generate_fix
from app.ai.provider import AIProvider, AIProviderError, AIProviderUnavailable
from app.api.routes.findings import provider_dependency
from app.db.fixes import get_fix, save_fix
from app.db.repository import get_finding
from app.db.session import get_db
from app.schemas.fix import FixSuggestionOut
from app.schemas.history import FINDING_ID_PATTERN
from app.services.history_service import to_finding

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/findings", tags=["fixes"])


@router.get("/{finding_id}/fix", response_model=FixSuggestionOut)
def get_stored_fix(
    finding_id: str = Path(pattern=FINDING_ID_PATTERN), session: Session = Depends(get_db)
) -> FixSuggestionOut:
    record = get_fix(session, finding_id)
    if record is None:
        raise HTTPException(status_code=404, detail="No fix suggestion has been generated yet.")
    return FixSuggestionOut.model_validate(record, from_attributes=True)


@router.post("/{finding_id}/suggest-fix", response_model=FixSuggestionOut)
def suggest_fix(
    finding_id: str = Path(pattern=FINDING_ID_PATTERN),
    refresh: bool = Query(default=False),
    session: Session = Depends(get_db),
    provider: AIProvider = Depends(provider_dependency),
) -> FixSuggestionOut:
    finding = get_finding(session, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found.")
    if not refresh:
        cached = get_fix(session, finding_id)
        if cached is not None:
            return FixSuggestionOut.model_validate(cached, from_attributes=True)

    try:
        proposal = generate_fix(provider, to_finding(finding))
    except NoSourceExcerpt as exc:
        raise HTTPException(
            status_code=422,
            detail="No usable source excerpt is stored for this finding, so a patch cannot be proposed.",
        ) from exc
    except AIProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc
    except AIProviderError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc

    try:
        saved = save_fix(session, finding, provider.name, provider.model, proposal)
    except SQLAlchemyError as exc:
        session.rollback()
        logger.exception("Could not save fix suggestion for finding %s", finding_id)
        raise HTTPException(
            status_code=500, detail="The suggestion was generated but could not be saved."
        ) from exc
    return FixSuggestionOut.model_validate(saved, from_attributes=True)
