"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import findings, fixes, health, scans
from app.core.config import get_settings
from app.core.middleware import (
    MULTIPART_OVERHEAD_BYTES,
    SecurityHeadersMiddleware,
    UploadLimitMiddleware,
)
from app.db.session import init_db

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield

def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name, version=settings.app_version, lifespan=lifespan
    )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": "Request could not be completed."})

    # The last middleware added is the outermost, so every response (including early
    # rejections) gets security headers, and CORS headers reach the browser on errors.
    application.add_middleware(
        UploadLimitMiddleware,
        limit=lambda: get_settings().max_upload_bytes + MULTIPART_OVERHEAD_BYTES,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )
    application.add_middleware(SecurityHeadersMiddleware)

    application.include_router(health.router, prefix="/api")
    application.include_router(scans.router, prefix="/api")
    application.include_router(findings.router, prefix="/api")
    application.include_router(fixes.router, prefix="/api")
    return application

app = create_app()
