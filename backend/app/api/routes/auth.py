"""Authentication routes: register, login, and user profile."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.auth import create_access_token, hash_password, verify_password
from app.db.models import UserRecord
from app.db.repository import create_user, get_user_by_email
from app.db.session import get_db
from app.schemas.auth import TokenResponse, UserLogin, UserOut, UserRegister

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, session: Session = Depends(get_db)) -> TokenResponse:
    """Create a new user account and return an access token."""
    existing = get_user_by_email(session, payload.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    hashed = hash_password(payload.password)
    user = create_user(session, payload.email, hashed)
    token = create_access_token(user.id)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, session: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate with email and password, returning an access token."""
    user = get_user_by_email(session, payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
def get_profile(current_user: UserRecord = Depends(get_current_user)) -> UserOut:
    """Return the profile of the currently logged-in user."""
    return UserOut.model_validate(current_user)
