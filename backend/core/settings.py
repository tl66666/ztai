from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _csv(name: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    value = os.environ.get(name)
    if value is None:
        return default
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _boolean(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value")


def _path(root: Path, value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else root / path


@dataclass(frozen=True)
class Settings:
    """Configuration interface shared by runtime and tests."""

    environment: str
    db_path: Path
    upload_folder: Path
    export_folder: Path
    allowed_origins: tuple[str, ...] = ()
    allowed_hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "testserver")
    api_docs_enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 5000
    workers: int = 1
    max_upload_bytes: int = 20 * 1024 * 1024

    @classmethod
    def from_environment(cls) -> Settings:
        default_root = Path(__file__).resolve().parents[2]
        project_root = Path(
            os.environ.get("JOBHUNTER_PROJECT_ROOT", default_root)
        ).expanduser().resolve()
        host = os.environ.get("JOBHUNTER_HOST", "127.0.0.1").strip()
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError(
                "JOBHUNTER_HOST must remain a loopback address until production authentication "
                "and tenant isolation are enabled"
            )
        port = int(os.environ.get("JOBHUNTER_PORT", "5000"))
        workers = int(os.environ.get("JOBHUNTER_WORKERS", "1"))
        if workers != 1:
            raise ValueError(
                "JOBHUNTER_WORKERS must remain 1 while the compatibility runtime uses SQLite"
            )
        local_origins = (
            f"http://localhost:{port}",
            f"http://127.0.0.1:{port}",
        )
        return cls(
            environment=os.environ.get("JOBHUNTER_ENV", "development"),
            db_path=_path(
                project_root,
                os.environ.get("JOBHUNTER_DB_PATH", "jobhunter.db"),
            ),
            upload_folder=_path(
                project_root,
                os.environ.get("JOBHUNTER_UPLOAD_FOLDER", "uploads"),
            ),
            export_folder=_path(
                project_root,
                os.environ.get("JOBHUNTER_EXPORT_FOLDER", "exports"),
            ),
            allowed_origins=_csv("JOBHUNTER_ALLOWED_ORIGINS", local_origins),
            allowed_hosts=_csv(
                "JOBHUNTER_ALLOWED_HOSTS",
                ("localhost", "127.0.0.1", "testserver"),
            ),
            api_docs_enabled=_boolean(
                "JOBHUNTER_API_DOCS",
                os.environ.get("JOBHUNTER_ENV", "development") != "production",
            ),
            host=host,
            port=port,
            workers=workers,
            max_upload_bytes=int(
                os.environ.get("JOBHUNTER_MAX_UPLOAD_BYTES", 20 * 1024 * 1024)
            ),
        )
