from __future__ import annotations

import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from backend.adapters.storage import CloudflareR2BlobStorage, LocalBlobStorage
from backend.core.settings import Settings
from backend.ports import BlobRef


class _FakeR2Client:
    def __init__(self):
        self.objects = {}

    def put_object(self, **kwargs):
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = {
            "content": kwargs["Body"].read(),
            "metadata": kwargs["Metadata"],
        }

    def get_object(self, **kwargs):
        stored = self.objects[(kwargs["Bucket"], kwargs["Key"])]
        return {
            "Body": BytesIO(stored["content"]),
            "Metadata": stored["metadata"],
        }

    def delete_object(self, **kwargs):
        self.objects.pop((kwargs["Bucket"], kwargs["Key"]), None)


class BlobStorageContractTests(unittest.TestCase):
    def test_local_reference_is_opaque_owned_and_checksum_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = LocalBlobStorage(directory)
            reference = storage.store(
                BytesIO(b"owned content"),
                original_name="../../resume.txt",
                namespace="resumes",
                owner_id=7,
                content_type="text/plain",
            )

            token = reference.to_token()
            restored = storage.restore(token, owner_id=7)
            with storage.open(restored) as source:
                self.assertEqual(source.read(), b"owned content")

            self.assertNotIn(str(Path(directory)), token)
            self.assertTrue(reference.object_key.startswith("owners/7/resumes/"))
            with self.assertRaises(PermissionError):
                storage.restore(token, owner_id=8)
            path = Path(directory) / reference.object_key
            path.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "checksum"):
                with storage.open(reference) as source:
                    source.read()

    def test_r2_adapter_persists_owner_and_checksum_metadata(self):
        client = _FakeR2Client()
        storage = CloudflareR2BlobStorage(
            account_id="account",
            bucket="bucket",
            access_key_id="access",
            secret_access_key="secret",
            client=client,
        )

        reference = storage.store(
            BytesIO(b"r2 content"),
            original_name="resume.pdf",
            namespace="resumes",
            owner_id=3,
            content_type="application/pdf",
        )
        with storage.open(reference) as source:
            self.assertEqual(source.read(), b"r2 content")
        stored = client.objects[("bucket", reference.object_key)]
        self.assertEqual(stored["metadata"]["owner-id"], "3")
        self.assertEqual(stored["metadata"]["sha256"], reference.checksum_sha256)

        storage.delete(reference)
        self.assertEqual(client.objects, {})

    def test_reference_rejects_invalid_tokens(self):
        with self.assertRaisesRegex(ValueError, "invalid blob reference"):
            BlobRef.from_token('{"version":2}')

    def test_r2_settings_require_complete_credentials(self):
        environment = {
            "JOBHUNTER_BLOB_STORAGE_BACKEND": "r2",
            "JOBHUNTER_R2_ACCOUNT_ID": "account",
        }
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(ValueError, "R2_BUCKET"):
                Settings.from_environment()


if __name__ == "__main__":
    unittest.main()
