from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager

from a2wsgi import WSGIMiddleware
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.api.career import create_career_router
from backend.api.interviews import create_interview_router
from backend.api.opportunities import create_opportunity_router
from backend.api.resume_intelligence import create_resume_intelligence_router
from backend.api.resumes import create_resume_router
from backend.api.system import create_system_router
from backend.application.container import ApplicationContainer
from backend.core.settings import Settings
from backend.security import (
    AuthenticationError,
    CloudflareAccessPrincipalProvider,
    LocalPrincipalProvider,
    PrincipalProvider,
)


def create_application(
    settings: Settings | None = None,
    *,
    principal_provider: PrincipalProvider | None = None,
) -> FastAPI:
    """Build the complete ASGI application behind one runtime interface."""

    runtime_settings = settings or Settings.from_environment()
    container = ApplicationContainer(runtime_settings)
    identity_provider = principal_provider or _principal_provider(
        runtime_settings,
        local_user_id=container.legacy.local_user_id,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        container.initialize()
        yield

    application = FastAPI(
        title="JobHunter API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/v1/docs" if runtime_settings.api_docs_enabled else None,
        redoc_url=None,
        openapi_url=("/api/v1/openapi.json" if runtime_settings.api_docs_enabled else None),
    )

    @application.middleware("http")
    async def authenticate(request: Request, call_next: Callable):
        if (
            not request.url.path.startswith("/api/")
            or request.url.path == "/api/v1/healthz"
            or request.method == "OPTIONS"
        ):
            return await call_next(request)
        try:
            request.state.principal = identity_provider.authenticate(request.headers)
        except AuthenticationError as exc:
            return JSONResponse(
                {
                    "success": False,
                    "message": str(exc),
                    "code": "authentication_failed",
                },
                status_code=401,
            )
        return await call_next(request)

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
        create_system_router(container.database_ready),
        prefix="/api/v1",
    )
    application.include_router(create_career_router(lambda: container.career))
    application.include_router(create_interview_router(lambda: container.interviews))
    application.include_router(create_opportunity_router(lambda: container.opportunities))
    application.include_router(create_resume_router(lambda: container.resumes))
    application.include_router(
        create_resume_intelligence_router(lambda: container.resume_intelligence)
    )
    application.mount("/", WSGIMiddleware(container.legacy.application))
    return application


def _principal_provider(
    settings: Settings,
    *,
    local_user_id: int,
) -> PrincipalProvider:
    if settings.auth_mode == "cloudflare_access":
        return CloudflareAccessPrincipalProvider(
            team_domain=settings.cloudflare_access_team_domain,
            audience=settings.cloudflare_access_audience,
            allowed_emails=settings.allowed_identity_emails,
            user_id=local_user_id,
        )
    return LocalPrincipalProvider(local_user_id)
