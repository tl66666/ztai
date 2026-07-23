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
    ai_config_path: Path | None = None
    auth_mode: str = "local"
    cloudflare_access_team_domain: str = ""
    cloudflare_access_audience: str = ""
    allowed_identity_emails: tuple[str, ...] = ()
    local_user_id: int = 1

    @classmethod
    def from_environment(cls) -> Settings:
        default_root = Path(__file__).resolve().parents[2]
        project_root = (
            Path(os.environ.get("JOBHUNTER_PROJECT_ROOT", default_root)).expanduser().resolve()
        )
        host = os.environ.get("JOBHUNTER_HOST", "127.0.0.1").strip()
        auth_mode = os.environ.get("JOBHUNTER_AUTH_MODE", "local").strip()
        if auth_mode not in {"local", "cloudflare_access"}:
            raise ValueError("JOBHUNTER_AUTH_MODE must be local or cloudflare_access")
        team_domain = os.environ.get("JOBHUNTER_CF_ACCESS_TEAM_DOMAIN", "").strip()
        audience = os.environ.get("JOBHUNTER_CF_ACCESS_AUDIENCE", "").strip()
        allowed_identity_emails = _csv("JOBHUNTER_ALLOWED_IDENTITY_EMAILS")
        if auth_mode == "cloudflare_access" and (
            not team_domain or not audience or not allowed_identity_emails
        ):
            raise ValueError(
                "Cloudflare Access authentication requires team domain, "
                "audience, and at least one allowed identity email"
            )
        if host not in {"127.0.0.1", "localhost", "::1"} and auth_mode != "cloudflare_access":
            raise ValueError(
                "JOBHUNTER_HOST may be public only when Cloudflare Access "
                "authentication is configured"
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
        allowed_origins = _csv("JOBHUNTER_ALLOWED_ORIGINS", local_origins)
        allowed_hosts = _csv(
            "JOBHUNTER_ALLOWED_HOSTS",
            ("localhost", "127.0.0.1", "testserver"),
        )
        local_user_id = int(os.environ.get("JOBHUNTER_AGENT_USER_ID", "1"))
        if local_user_id <= 0:
            raise ValueError("JOBHUNTER_AGENT_USER_ID must be positive")
        if auth_mode == "cloudflare_access":
            if (
                "JOBHUNTER_ALLOWED_ORIGINS" not in os.environ
                or "JOBHUNTER_ALLOWED_HOSTS" not in os.environ
                or not allowed_origins
                or not allowed_hosts
                or "*" in allowed_origins
                or "*" in allowed_hosts
            ):
                raise ValueError(
                    "Cloudflare Access mode requires explicit non-wildcard "
                    "allowed origins and hosts"
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
            allowed_origins=allowed_origins,
            allowed_hosts=allowed_hosts,
            api_docs_enabled=_boolean(
                "JOBHUNTER_API_DOCS",
                os.environ.get("JOBHUNTER_ENV", "development") != "production",
            ),
            host=host,
            port=port,
            workers=workers,
            max_upload_bytes=int(os.environ.get("JOBHUNTER_MAX_UPLOAD_BYTES", 20 * 1024 * 1024)),
            ai_config_path=_path(
                project_root,
                os.environ.get(
                    "JOBHUNTER_AI_CONFIG_PATH",
                    "output/runtime/ai-config.json",
                ),
            ),
            auth_mode=auth_mode,
            cloudflare_access_team_domain=team_domain,
            cloudflare_access_audience=audience,
            allowed_identity_emails=allowed_identity_emails,
            local_user_id=local_user_id,
        )
