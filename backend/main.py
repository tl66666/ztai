from __future__ import annotations

from contextlib import asynccontextmanager

from a2wsgi import WSGIMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.adapters.legacy_flask import LegacyFlaskAdapter
from backend.api.system import create_system_router
from backend.core.settings import Settings


def create_application(settings: Settings | None = None) -> FastAPI:
    """Build the complete ASGI application behind one runtime interface."""

    runtime_settings = settings or Settings.from_environment()
    legacy = LegacyFlaskAdapter(runtime_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        legacy.initialize()
        yield

    application = FastAPI(
        title="JobHunter API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/v1/docs" if runtime_settings.api_docs_enabled else None,
        redoc_url=None,
        openapi_url=(
            "/api/v1/openapi.json" if runtime_settings.api_docs_enabled else None
        ),
    )
    if runtime_settings.allowed_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(runtime_settings.allowed_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )
    if runtime_settings.allowed_hosts:
        application.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=list(runtime_settings.allowed_hosts),
        )
    application.include_router(
        create_system_router(legacy.database_ready),
        prefix="/api/v1",
    )
    application.mount("/", WSGIMiddleware(legacy.application))
    return application
