from __future__ import annotations

from pathlib import Path

from backend.core.database import Database, resolve_database_url


class RuntimeDatabase:
    """Own schema initialization and readiness for one application runtime."""

    def __init__(
        self,
        db_path: str | Path,
        *,
        upload_folder: str | Path,
        export_folder: str | Path,
        local_user_id: int,
        database_url: str | None = None,
    ):
        self.db_path = Path(db_path)
        self.upload_folder = Path(upload_folder)
        self.export_folder = Path(export_folder)
        self.local_user_id = int(local_user_id)
        self.database_url = resolve_database_url(database_url, self.db_path)
        self.database = Database(self.database_url)

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.upload_folder.mkdir(parents=True, exist_ok=True)
        self.export_folder.mkdir(parents=True, exist_ok=True)
        self.database.upgrade()
        self.database.ensure_local_user(self.local_user_id)

    def ready(self) -> bool:
        return self.database.is_ready()

    def close(self) -> None:
        self.database.dispose()
