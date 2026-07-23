from __future__ import annotations

import json
from contextlib import AbstractContextManager
from dataclasses import asdict, dataclass
from typing import BinaryIO, Protocol


@dataclass(frozen=True)
class BlobRef:
    """Serializable object identity with no filesystem or provider details."""

    backend: str
    owner_id: int
    object_key: str
    checksum_sha256: str
    size_bytes: int
    content_type: str

    def to_token(self) -> str:
        return json.dumps(
            {"version": 1, **asdict(self)},
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )

    @classmethod
    def from_token(cls, token: str) -> BlobRef:
        try:
            payload = json.loads(token)
            if not isinstance(payload, dict) or payload.pop("version", None) != 1:
                raise ValueError
            reference = cls(**payload)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("invalid blob reference") from exc
        if (
            reference.owner_id <= 0
            or reference.size_bytes < 0
            or len(reference.checksum_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in reference.checksum_sha256
            )
            or not reference.object_key
            or not reference.backend
            or not reference.content_type
        ):
            raise ValueError("invalid blob reference")
        return reference


class BlobStorage(Protocol):
    """Opaque persistence interface for user-owned binary objects."""

    def store(
        self,
        source: BinaryIO,
        *,
        original_name: str,
        namespace: str,
        owner_id: int,
        content_type: str = "application/octet-stream",
    ) -> BlobRef: ...

    def open(self, reference: BlobRef) -> AbstractContextManager[BinaryIO]: ...

    def delete(self, reference: BlobRef) -> None: ...

    def restore(self, token: str, *, owner_id: int) -> BlobRef: ...
