from __future__ import annotations

from backend.core.settings import Settings
from backend.ports.blob_storage import BlobStorage

from .local import LocalBlobStorage
from .r2 import CloudflareR2BlobStorage


def create_blob_storage(settings: Settings) -> BlobStorage:
    if settings.blob_storage_backend == "r2":
        return CloudflareR2BlobStorage(
            account_id=settings.r2_account_id,
            bucket=settings.r2_bucket,
            access_key_id=settings.r2_access_key_id,
            secret_access_key=settings.r2_secret_access_key,
            endpoint_url=settings.r2_endpoint_url or None,
            max_bytes=settings.max_upload_bytes,
        )
    return LocalBlobStorage(
        settings.upload_folder,
        max_bytes=settings.max_upload_bytes,
    )
