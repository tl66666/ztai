from __future__ import annotations

import os
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any

from backend.core.database import Database, sqlite_database_url

from .unit_of_work import SqlAlchemyUnitOfWork


def coerce_unit_of_work_factory(source: Any) -> Callable[[], SqlAlchemyUnitOfWork]:
    """Compatibility seam for old tests; production injects its existing factory."""
    if callable(source) and not isinstance(source, (str, bytes, os.PathLike)):
        return source
    database = Database(sqlite_database_url(Path(os.fspath(source))))
    factory = partial(SqlAlchemyUnitOfWork, database.session_factory)
    setattr(factory, "_database_owner", database)
    return factory
