from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from backend.documents import ALLOWED_RESUME_EXTENSIONS
from backend.ports import BlobStorage
from backend.ports.persistence import UnitOfWorkFactory

from .resume_blobs import ResumeBlobModule
from .resume_exports import ResumeExport, ResumeExportModule


@dataclass(frozen=True)
class ResumeOriginal:
    content: bytes
    filename: str
    media_type: str


class ResumeModule:
    """Own resume CRUD, upload ownership, and safe blob persistence."""

    def __init__(
        self,
        unit_of_work: UnitOfWorkFactory,
        storage: BlobStorage,
        export_folder: str | Path,
        *,
        local_user_id: int,
    ):
        self._unit_of_work = unit_of_work
        self._storage = storage
        self._blobs = ResumeBlobModule(storage, owner_id=local_user_id)
        self._exports = ResumeExportModule(self._blobs, export_folder)
        self._local_user_id = int(local_user_id)

    def create_text(self, body: dict[str, Any]) -> tuple[dict[str, Any], int]:
        self._require_local_user(body.get("user_id"))
        title = str(body.get("title") or "").strip()
        content = str(body.get("content") or "").strip()
        if not title or not content:
            raise ValueError("标题和内容不能为空。")
        resume_id = self._insert(title, content, None, None)
        return self._created_payload(resume_id, content), 201

    def create_upload(
        self,
        source: BinaryIO,
        *,
        filename: str,
        title: str | None = None,
        requested_user_id: int | str | None = None,
    ) -> tuple[dict[str, Any], int]:
        self._require_local_user(requested_user_id)
        file_type = self._validated_extension(filename)
        blob, content = self._blobs.store_and_parse(
            source,
            filename=filename,
            file_type=file_type,
        )
        try:
            resume_id = self._insert(
                (title or filename or "未命名简历").strip(),
                content,
                blob.to_token(),
                file_type,
            )
        except Exception:
            self._storage.delete(blob)
            raise
        return self._created_payload(resume_id, content), 201

    def list(self, requested_user_id: int) -> dict[str, Any]:
        self._require_local_user(requested_user_id)
        with self._unit_of_work() as unit_of_work:
            rows = unit_of_work.resumes.list_owned(self._local_user_id)
        return {
            "success": True,
            "data": [self._public_resume(row) for row in rows],
        }

    def detail(self, resume_id: int) -> tuple[dict[str, Any], int]:
        row = self._owned_resume(resume_id)
        if row is None:
            return {"success": False, "message": "简历不存在"}, 404
        return {"success": True, "data": self._public_resume(row)}, 200

    def original(self, resume_id: int) -> ResumeOriginal:
        row = self._owned_resume(resume_id)
        if row is None:
            raise LookupError("简历不存在")
        reference_token = row["file_path"]
        if not reference_token:
            raise LookupError("这份简历没有保存原始文件，只能编辑文本内容。")
        content, media_type = self._blobs.read(reference_token)
        suffix = f".{str(row['file_type'] or '').lower()}"
        return ResumeOriginal(
            content=content,
            filename=f"{row['title']}{suffix}",
            media_type=media_type,
        )

    def replace_upload(
        self,
        resume_id: int,
        source: BinaryIO,
        *,
        filename: str,
    ) -> dict[str, Any]:
        existing = self._owned_resume(resume_id)
        if existing is None:
            raise LookupError("简历不存在")
        file_type = self._validated_extension(filename)
        blob, content = self._blobs.store_and_parse(
            source,
            filename=filename,
            file_type=file_type,
        )
        try:
            with self._unit_of_work() as unit_of_work:
                unit_of_work.resumes.replace_upload(
                    resume_id,
                    self._local_user_id,
                    file_path=blob.to_token(),
                    file_type=file_type,
                    content=content,
                )
        except Exception:
            self._storage.delete(blob)
            raise
        if existing.get("file_path"):
            with suppress(Exception):
                self._blobs.delete(existing["file_path"])
        return {
            "success": True,
            "message": "原文件已替换并重新解析",
            "parsed_content": content[:1000],
        }

    def update(
        self, resume_id: int, body: dict[str, Any]
    ) -> tuple[dict[str, Any], int]:
        title = str(body.get("title") or "").strip()
        content = str(body.get("content") or "").strip()
        if not title or not content:
            raise ValueError("标题和内容不能为空")
        with self._unit_of_work() as unit_of_work:
            updated = unit_of_work.resumes.update_text(
                resume_id,
                self._local_user_id,
                title=title,
                content=content,
            )
        if not updated:
            return {"success": False, "message": "简历不存在"}, 404
        return {"success": True, "message": "简历已更新"}, 200

    def delete(self, resume_id: int) -> tuple[dict[str, Any], int]:
        existing = self._owned_resume(resume_id)
        with self._unit_of_work() as unit_of_work:
            deleted = unit_of_work.resumes.delete_owned(
                resume_id,
                self._local_user_id,
            )
        if not deleted:
            return {"success": False, "message": "简历不存在"}, 404
        if existing and existing.get("file_path"):
            with suppress(Exception):
                self._blobs.delete(existing["file_path"])
        return {"success": True, "message": "简历已删除"}, 200

    def export(self, resume_id: int, format_type: str) -> ResumeExport:
        row = self._owned_resume(resume_id)
        if row is None:
            raise LookupError("简历不存在")
        return self._exports.export(dict(row), format_type)

    def _insert(
        self,
        title: str,
        content: str,
        file_path: str | None,
        file_type: str | None,
    ) -> int:
        with self._unit_of_work() as unit_of_work:
            return unit_of_work.resumes.add(
                self._local_user_id,
                title=title,
                content=content,
                file_path=file_path,
                file_type=file_type,
            )

    def _owned_resume(self, resume_id: int):
        with self._unit_of_work() as unit_of_work:
            return unit_of_work.resumes.get_owned(resume_id, self._local_user_id)

    def _require_local_user(self, requested_user_id: int | str | None) -> None:
        if requested_user_id in (None, ""):
            return
        try:
            normalized = int(requested_user_id)
        except (TypeError, ValueError) as exc:
            raise PermissionError("当前本地版本仅允许访问当前用户数据") from exc
        if normalized != self._local_user_id:
            raise PermissionError("当前本地版本仅允许访问当前用户数据")

    @staticmethod
    def _validated_extension(filename: str) -> str:
        suffix = Path(filename or "").suffix.lower().lstrip(".")
        if suffix not in ALLOWED_RESUME_EXTENSIONS:
            raise ValueError("请上传 PDF、Word、TXT 或图片格式简历。")
        return suffix

    @staticmethod
    def _created_payload(resume_id: int, content: str) -> dict[str, Any]:
        return {
            "success": True,
            "message": "简历已保存",
            "resume_id": resume_id,
            "parsed_content": content[:1000],
        }

    @staticmethod
    def _public_resume(row) -> dict[str, Any]:
        resume = dict(row)
        resume["has_original"] = bool(resume.pop("file_path", None))
        return resume
