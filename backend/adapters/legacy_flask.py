from __future__ import annotations

import importlib.util
import sqlite3
import uuid
from pathlib import Path
from types import ModuleType

from backend.core.settings import Settings


class LegacyFlaskAdapter:
    """Expose the existing Flask application behind the ASGI migration seam."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._legacy = self._load_isolated_application_module()
        self._configure()

    @property
    def application(self):
        return self._legacy.app

    @property
    def local_user_id(self) -> int:
        return int(self._legacy.AGENT_USER_ID)

    @property
    def career_service(self):
        return self._legacy.get_career_service()

    @property
    def interview_service(self):
        return self._legacy.get_interview_service()

    def initialize(self) -> None:
        self.settings.upload_folder.mkdir(parents=True, exist_ok=True)
        self.settings.export_folder.mkdir(parents=True, exist_ok=True)
        self._legacy.init_db()

    def database_ready(self) -> bool:
        if not self.settings.db_path.is_file():
            return False
        try:
            database_uri = f"{self.settings.db_path.resolve().as_uri()}?mode=ro"
            with sqlite3.connect(database_uri, uri=True) as connection:
                connection.execute("SELECT 1").fetchone()
        except sqlite3.Error:
            return False
        return True

    @staticmethod
    def _load_isolated_application_module() -> ModuleType:
        module_path = Path(__file__).resolve().parents[2] / "app.py"
        module_name = f"_jobhunter_legacy_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load legacy application from {module_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _configure(self) -> None:
        legacy = self._legacy
        legacy.DB_PATH = str(self.settings.db_path)
        legacy.UPLOAD_FOLDER = str(self.settings.upload_folder)
        legacy.EXPORT_FOLDER = str(self.settings.export_folder)
        legacy.app.config["UPLOAD_FOLDER"] = str(self.settings.upload_folder)
        legacy._agent_service = None
        legacy._agent_action_service = None
        legacy._interview_service = None
