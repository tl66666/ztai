from __future__ import annotations

import uuid
from pathlib import Path
from typing import BinaryIO

from backend.ports.blob_storage import StoredBlob


class LocalBlobStorage:
    """Filesystem adapter using generated object keys, never client paths."""

    def __init__(self, root: str | Path, *, max_bytes: int = 20 * 1024 * 1024):
        self._root = Path(root)
        self._max_bytes = max_bytes

    def store(
        self,
        source: BinaryIO,
        *,
        original_name: str,
        namespace: str,
    ) -> StoredBlob:
        suffix = Path(original_name).suffix.lower()
        object_key = f"{namespace}/{uuid.uuid4().hex}{suffix}"
        target = self._root / object_key
        target.parent.mkdir(parents=True, exist_ok=True)
        source.seek(0)
        size = 0
        try:
            with target.open("wb") as destination:
                while chunk := source.read(1024 * 1024):
                    size += len(chunk)
                    if size > self._max_bytes:
                        raise ValueError("上传文件不能超过 20 MB")
                    destination.write(chunk)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return StoredBlob(object_key=object_key, local_path=target)
