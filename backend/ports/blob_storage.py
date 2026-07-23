from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol


@dataclass(frozen=True)
class StoredBlob:
    """Opaque object identity plus the local compatibility location."""

    object_key: str
    local_path: Path


class BlobStorage(Protocol):
    """Persistence interface for user-supplied binary objects."""

    def store(
        self,
        source: BinaryIO,
        *,
        original_name: str,
        namespace: str,
    ) -> StoredBlob: ...
