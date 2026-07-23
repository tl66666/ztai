"""Stable infrastructure interfaces used by application modules."""

from .blob_storage import BlobStorage, StoredBlob

__all__ = ["BlobStorage", "StoredBlob"]
