from __future__ import annotations

import uvicorn

from backend.core.settings import Settings


def main() -> None:
    """Start the cross-platform ASGI runtime from environment configuration."""

    settings = Settings.from_environment()
    uvicorn.run(
        "backend.main:create_application",
        factory=True,
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        proxy_headers=True,
        forwarded_allow_ips="127.0.0.1",
    )


if __name__ == "__main__":
    main()
