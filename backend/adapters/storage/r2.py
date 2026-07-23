from __future__ import annotations

import hashlib
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, BinaryIO

from backend.ports.blob_storage import BlobRef

from .keying import object_key
from .keying import owner_id as normalize_owner_id


class CloudflareR2BlobStorage:
    """Cloudflare R2 adapter using the S3-compatible API."""

    backend_name = "r2"

    def __init__(
        self,
        *,
        account_id: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        max_bytes: int = 20 * 1024 * 1024,
        endpoint_url: str | None = None,
        client: Any | None = None,
    ):
        values = {
            "account_id": account_id,
            "bucket": bucket,
            "access_key_id": access_key_id,
            "secret_access_key": secret_access_key,
        }
        missing = [name for name, value in values.items() if not str(value).strip()]
        if missing:
            raise ValueError(f"R2 configuration missing: {', '.join(missing)}")
        self._bucket = bucket.strip()
        self._max_bytes = int(max_bytes)
        if client is None:
            import boto3

            client = boto3.client(
                "s3",
                endpoint_url=endpoint_url
                or f"https://{account_id.strip()}.r2.cloudflarestorage.com",
                aws_access_key_id=access_key_id.strip(),
                aws_secret_access_key=secret_access_key.strip(),
                region_name="auto",
            )
        self._client = client

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
        digest = hashlib.sha256()
        size = 0
        with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024) as payload:
            source.seek(0)
            while chunk := source.read(1024 * 1024):
                size += len(chunk)
                if size > self._max_bytes:
                    raise ValueError("上传文件不能超过 20 MB")
                digest.update(chunk)
                payload.write(chunk)
            checksum = digest.hexdigest()
            payload.seek(0)
            self._client.put_object(
                Bucket=self._bucket,
                Key=generated_key,
                Body=payload,
                ContentType=content_type or "application/octet-stream",
                Metadata={
                    "owner-id": str(normalized_owner),
                    "sha256": checksum,
                },
            )
        return BlobRef(
            backend=self.backend_name,
            owner_id=normalized_owner,
            object_key=generated_key,
            checksum_sha256=checksum,
            size_bytes=size,
            content_type=content_type or "application/octet-stream",
        )

    @contextmanager
    def open(self, reference: BlobRef) -> Iterator[BinaryIO]:
        self._validate(reference)
        response = self._client.get_object(
            Bucket=self._bucket,
            Key=reference.object_key,
        )
        metadata = response.get("Metadata") or {}
        if (
            metadata.get("owner-id") != str(reference.owner_id)
            or metadata.get("sha256") != reference.checksum_sha256
        ):
            response["Body"].close()
            raise ValueError("blob metadata validation failed")
        digest = hashlib.sha256()
        size = 0
        with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024) as payload:
            body = response["Body"]
            try:
                while chunk := body.read(1024 * 1024):
                    size += len(chunk)
                    if size > self._max_bytes:
                        raise ValueError("stored blob exceeds configured size limit")
                    digest.update(chunk)
                    payload.write(chunk)
            finally:
                body.close()
            if size != reference.size_bytes or digest.hexdigest() != reference.checksum_sha256:
                raise ValueError("blob checksum validation failed")
            payload.seek(0)
            yield payload

    def delete(self, reference: BlobRef) -> None:
        self._validate(reference)
        self._client.delete_object(Bucket=self._bucket, Key=reference.object_key)

    def restore(self, token: str, *, owner_id: int) -> BlobRef:
        reference = BlobRef.from_token(token)
        self._validate(reference, owner_id=normalize_owner_id(owner_id))
        return reference

    def _validate(self, reference: BlobRef, *, owner_id: int | None = None) -> None:
        expected_owner = reference.owner_id if owner_id is None else owner_id
        if (
            reference.backend != self.backend_name
            or reference.owner_id != expected_owner
            or not reference.object_key.startswith(f"owners/{reference.owner_id}/")
        ):
            raise PermissionError("blob owner mismatch")
