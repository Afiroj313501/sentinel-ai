"""Database engine and session handling."""

from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.models import Base


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    is_sqlite = url.startswith("sqlite")
    if url.startswith("sqlite:///"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(
        url, connect_args={"check_same_thread": False} if is_sqlite else {}
    )


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Create tables if they do not exist yet."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    _migrate_existing_schema(engine)


def _migrate_existing_schema(engine: Engine) -> None:
    """Apply additive changes to databases created by older application versions."""
    if "user_id" not in {column["name"] for column in inspect(engine).get_columns("scans")}:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE scans ADD COLUMN user_id VARCHAR(36) "
                    "REFERENCES users(id)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_scans_user_id "
                    "ON scans (user_id)"
                )
            )


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a database session."""
    with _session_factory()() as session:
        yield session
