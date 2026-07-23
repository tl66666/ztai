from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from backend.core.settings import Settings
from backend.main import create_application


class CompatibleResponse:
    """Small Flask-response compatibility shim for migrated API tests."""

    def __init__(self, response):
        self._response = response

    def __getattr__(self, name: str):
        return getattr(self._response, name)

    def get_json(self):
        return self._response.json()

    def get_data(self, *, as_text: bool = False):
        return self._response.text if as_text else self._response.content


class CompatibleClient:
    """Keep existing assertions readable while using the native ASGI runtime."""

    def __init__(self, client: TestClient):
        self._client = client

    def get(self, path: str, **kwargs: Any) -> CompatibleResponse:
        return CompatibleResponse(self._client.get(path, **kwargs))

    def post(
        self,
        path: str,
        *,
        content_type: str | None = None,
        data: Any = None,
        **kwargs: Any,
    ) -> CompatibleResponse:
        if content_type is not None:
            headers = dict(kwargs.pop("headers", {}))
            headers["Content-Type"] = content_type
            kwargs["headers"] = headers
        if data is not None:
            if content_type is None and isinstance(data, dict):
                kwargs["data"] = data
            else:
                kwargs["content"] = data
        return CompatibleResponse(self._client.post(path, **kwargs))


def create_agent_test_runtime(
    root: str | Path,
    *,
    db_name: str = "api.db",
) -> tuple[TestClient, CompatibleClient]:
    base = Path(root)
    settings = Settings(
        environment="test",
        db_path=base / db_name,
        upload_folder=base / "uploads",
        export_folder=base / "exports",
        allowed_origins=(
            "http://localhost:5000",
            "http://127.0.0.1:5000",
        ),
    )
    raw_client = TestClient(create_application(settings))
    return raw_client, CompatibleClient(raw_client)
