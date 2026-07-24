from collections.abc import Callable

from fastapi import APIRouter, Response, status


def create_system_router(database_ready: Callable[[], bool]) -> APIRouter:
    router = APIRouter(tags=["system"])

    @router.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "jobhunter-api"}

    @router.get("/readyz")
    def readiness(response: Response) -> dict[str, object]:
        if not database_ready():
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {
                "status": "not_ready",
                "checks": {"database": "unavailable"},
            }
        return {
            "status": "ready",
            "checks": {"database": "ok"},
        }

    return router
