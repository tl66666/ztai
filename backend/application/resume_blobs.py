from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

from backend.documents import parse_resume_file
from backend.ports import BlobRef, BlobStorage


class ResumeBlobModule:
    """Materialize opaque resume blobs only at document-library seams."""

    def __init__(self, storage: BlobStorage, *, owner_id: int):
        self._storage = storage
        self._owner_id = int(owner_id)

    def store_and_parse(
        self,
        source: BinaryIO,
        *,
        filename: str,
        file_type: str,
    ) -> tuple[BlobRef, str]:
        reference = self._storage.store(
            source,
            original_name=filename,
            namespace="resumes",
            owner_id=self._owner_id,
        )
        try:
            with self.materialize(reference.to_token(), suffix=f".{file_type}") as path:
                content = parse_resume_file(path, file_type)
        except Exception:
            self._storage.delete(reference)
            raise
        return reference, content

    @contextmanager
    def materialize(self, token: str, *, suffix: str) -> Iterator[Path]:
        reference = self._storage.restore(token, owner_id=self._owner_id)
        with tempfile.TemporaryDirectory(prefix="jobhunter-resume-") as directory:
            path = Path(directory) / f"original{suffix}"
            with self._storage.open(reference) as source, path.open("wb") as destination:
                shutil.copyfileobj(source, destination)
            yield path

    def read(self, token: str) -> tuple[bytes, str]:
        reference = self._storage.restore(token, owner_id=self._owner_id)
        with self._storage.open(reference) as source:
            return source.read(), reference.content_type

    def copy_to(self, token: str, target: Path) -> None:
        reference = self._storage.restore(token, owner_id=self._owner_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        with self._storage.open(reference) as source, target.open("wb") as destination:
            shutil.copyfileobj(source, destination)

    def delete(self, token: str) -> None:
        reference = self._storage.restore(token, owner_id=self._owner_id)
        self._storage.delete(reference)
