from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import BinaryIO


class LocalTrainingAudioStorage:
    """Local compatibility adapter for recorded interview audio."""

    def __init__(self, root: str | Path, *, max_bytes: int):
        self._root = Path(root)
        self._max_bytes = max_bytes

    def store(self, source: BinaryIO, original_name: str) -> str:
        safe_name = self._safe_filename(
            f"audio_{uuid.uuid4().hex[:8]}_{original_name}"
        )
        target = self._root / safe_name
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
        return safe_name

    def delete(self, object_key: str) -> None:
        target = (self._root / object_key).resolve()
        root = self._root.resolve()
        if target != root and root in target.parents:
            target.unlink(missing_ok=True)

    @staticmethod
    def _safe_filename(name: str) -> str:
        return (
            re.sub(r"[^\w\u4e00-\u9fa5.-]+", "_", name or "audio")
            .strip("._")
            or "audio"
        )
