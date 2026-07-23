from __future__ import annotations

import hashlib
import mimetypes
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

from backend.ports.blob_storage import BlobRef

from .keying import object_key
from .keying import owner_id as normalize_owner_id


class LocalBlobStorage:
    """Filesystem adapter with the same ownership contract as object storage."""

    backend_name = "local"

    def __init__(self, root: str | Path, *, max_bytes: int = 20 * 1024 * 1024):
        self._root = Path(root).expanduser().resolve()
        self._max_bytes = int(max_bytes)

    def store(
        self,
        source: BinaryIO,
        *,
        original_name: str,
        namespace: str,
        owner_id: int,
        content_type: str = "application/octet-stream",
    ) -> BlobRef:
        normalized_owner = normalize_owner_id(owner_id)
        generated_key = object_key(
            owner=normalized_owner,
            namespace=namespace,
            original_name=original_name,
        )
        target = self._path(generated_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        source.seek(0)
        size = 0
        digest = hashlib.sha256()
        try:
            with target.open("xb") as destination:
                while chunk := source.read(1024 * 1024):
                    size += len(chunk)
                    if size > self._max_bytes:
                        raise ValueError("上传文件不能超过 20 MB")
                    digest.update(chunk)
                    destination.write(chunk)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return BlobRef(
            backend=self.backend_name,
            owner_id=normalized_owner,
            object_key=generated_key,
            checksum_sha256=digest.hexdigest(),
            size_bytes=size,
            content_type=(
                content_type
                if content_type and content_type != "application/octet-stream"
                else mimetypes.guess_type(original_name)[0] or "application/octet-stream"
            ),
        )

    @contextmanager
    def open(self, reference: BlobRef) -> Iterator[BinaryIO]:
        self._validate(reference)
        path = self._path(reference.object_key)
        try:
            stream = path.open("rb")
        except FileNotFoundError as exc:
            raise LookupError("文件不存在或已被删除") from exc
        with stream:
            digest = hashlib.sha256()
            size = 0
            while chunk := stream.read(1024 * 1024):
                size += len(chunk)
                digest.update(chunk)
            if size != reference.size_bytes or digest.hexdigest() != reference.checksum_sha256:
                raise ValueError("blob checksum validation failed")
            stream.seek(0)
            yield stream

    def delete(self, reference: BlobRef) -> None:
        self._validate(reference)
        self._path(reference.object_key).unlink(missing_ok=True)

    def restore(self, token: str, *, owner_id: int) -> BlobRef:
        normalized_owner = normalize_owner_id(owner_id)
        try:
            reference = BlobRef.from_token(token)
        except ValueError:
            return self._restore_legacy_path(token, owner_id=normalized_owner)
        self._validate(reference, owner_id=normalized_owner)
        return reference

    def _restore_legacy_path(self, value: str, *, owner_id: int) -> BlobRef:
        """Adopt pre-BlobRef local rows without exposing paths to the application."""
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = self._root / candidate
        path = candidate.resolve()
        if self._root not in path.parents or not path.is_file():
            raise ValueError("invalid blob reference")
        relative = path.relative_to(self._root).as_posix()
        legacy_owner_parts = set(relative.split("/"))
        if str(owner_id) not in legacy_owner_parts:
            raise PermissionError("blob owner mismatch")
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                size += len(chunk)
                digest.update(chunk)
        return BlobRef(
            backend=self.backend_name,
            owner_id=owner_id,
            object_key=relative,
            checksum_sha256=digest.hexdigest(),
            size_bytes=size,
            content_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        )

    def _validate(self, reference: BlobRef, *, owner_id: int | None = None) -> None:
        expected_owner = reference.owner_id if owner_id is None else owner_id
        prefix = f"owners/{reference.owner_id}/"
        is_legacy_owned = f"/{reference.owner_id}/" in f"/{reference.object_key}/"
        if (
            reference.backend != self.backend_name
            or reference.owner_id != expected_owner
            or (
                not reference.object_key.startswith(prefix)
                and not is_legacy_owned
            )
        ):
            raise PermissionError("blob owner mismatch")
        self._path(reference.object_key)

    def _path(self, object_key: str) -> Path:
        target = (self._root / object_key).resolve()
        if target == self._root or self._root not in target.parents:
            raise ValueError("invalid blob object key")
        return target
