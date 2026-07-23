from __future__ import annotations

import sqlite3
from pathlib import Path

from utils.agent_runtime.memory import create_agent_tables
from utils.domain.database import connect, ensure_local_user, migrate_database


class RuntimeDatabase:
    """Own schema initialization and readiness for one application runtime."""

    def __init__(
        self,
        db_path: str | Path,
        *,
        upload_folder: str | Path,
        export_folder: str | Path,
        local_user_id: int,
    ):
        self.db_path = Path(db_path)
        self.upload_folder = Path(upload_folder)
        self.export_folder = Path(export_folder)
        self.local_user_id = int(local_user_id)

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.upload_folder.mkdir(parents=True, exist_ok=True)
        self.export_folder.mkdir(parents=True, exist_ok=True)
        migrate_database(self.db_path)
        with connect(self.db_path) as connection:
            ensure_local_user(connection, self.local_user_id)
        create_agent_tables(str(self.db_path))

    def ready(self) -> bool:
        if not self.db_path.is_file():
            return False
        try:
            database_uri = f"{self.db_path.resolve().as_uri()}?mode=ro"
            with sqlite3.connect(database_uri, uri=True) as connection:
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                connection.execute("SELECT 1").fetchone()
        except sqlite3.Error:
            return False
        return version > 0
