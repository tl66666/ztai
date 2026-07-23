from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from backend.documents import (
    ALLOWED_RESUME_EXTENSIONS,
    build_resume_docx,
    build_resume_pdf,
    parse_resume_file,
)
from backend.documents.conversion import (
    convert_pdf_to_word,
    convert_word_to_pdf,
)
from backend.ports import BlobStorage
from backend.ports.persistence import UnitOfWorkFactory


@dataclass(frozen=True)
class ResumeExport:
    path: Path
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
        self._export_folder = Path(export_folder)
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
        blob = self._storage.store(
            source,
            original_name=filename,
            namespace=f"resumes/{self._local_user_id}",
        )
        content = parse_resume_file(blob.local_path, file_type)
        resume_id = self._insert(
            (title or filename or "未命名简历").strip(),
            content,
            str(blob.local_path),
            file_type,
        )
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

    def original(self, resume_id: int) -> tuple[Path, str]:
        row = self._owned_resume(resume_id)
        if row is None:
            raise LookupError("简历不存在")
        original_path = row["file_path"]
        if not original_path or not Path(original_path).is_file():
            raise LookupError("这份简历没有保存原始文件，只能编辑文本内容。")
        path = Path(original_path)
        return path, f"{row['title']}{path.suffix.lower()}"

    def replace_upload(
        self,
        resume_id: int,
        source: BinaryIO,
        *,
        filename: str,
    ) -> dict[str, Any]:
        if self._owned_resume(resume_id) is None:
            raise LookupError("简历不存在")
        file_type = self._validated_extension(filename)
        blob = self._storage.store(
            source,
            original_name=filename,
            namespace=f"resumes/{self._local_user_id}",
        )
        content = parse_resume_file(blob.local_path, file_type)
        with self._unit_of_work() as unit_of_work:
            unit_of_work.resumes.replace_upload(
                resume_id,
                self._local_user_id,
                file_path=str(blob.local_path),
                file_type=file_type,
                content=content,
            )
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
        with self._unit_of_work() as unit_of_work:
            deleted = unit_of_work.resumes.delete_owned(
                resume_id,
                self._local_user_id,
            )
        if not deleted:
            return {"success": False, "message": "简历不存在"}, 404
        return {"success": True, "message": "简历已删除"}, 200

    def export(self, resume_id: int, format_type: str) -> ResumeExport:
        row = self._owned_resume(resume_id)
        if row is None:
            raise LookupError("简历不存在")
        normalized = format_type.lower()
        if normalized not in {"pdf", "word", "docx"}:
            raise ValueError("仅支持 PDF 或 Word 导出")

        extension = "pdf" if normalized == "pdf" else "docx"
        filename = self._safe_filename(row["title"], f".{extension}")
        self._export_folder.mkdir(parents=True, exist_ok=True)
        output_path = self._export_folder / f"{uuid.uuid4().hex}_{filename}"
        original = Path(row["file_path"]) if row["file_path"] else None
        original_type = str(row["file_type"] or "").lower()

        if original and original.is_file():
            if extension == "docx" and original_type == "docx":
                return ResumeExport(
                    original,
                    filename,
                    self._media_type(extension),
                )
            if extension == "pdf" and original_type == "pdf":
                return ResumeExport(
                    original,
                    filename,
                    self._media_type(extension),
                )
            if (
                extension == "pdf"
                and original_type in {"doc", "docx"}
                and convert_word_to_pdf(original, output_path)
            ):
                return ResumeExport(
                    output_path,
                    filename,
                    self._media_type(extension),
                )
            if extension == "docx" and original_type == "pdf":
                try:
                    convert_pdf_to_word(original, output_path)
                except Exception:
                    pass
                else:
                    return ResumeExport(
                        output_path,
                        filename,
                        self._media_type(extension),
                    )

        public_row = dict(row)
        if extension == "pdf":
            build_resume_pdf(public_row, output_path)
        else:
            build_resume_docx(public_row, output_path)
        return ResumeExport(
            output_path,
            filename,
            self._media_type(extension),
        )

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

    @staticmethod
    def _safe_filename(name: str, suffix: str) -> str:
        stem = (
            re.sub(r"[^\w\u4e00-\u9fa5.-]+", "_", name or "resume")
            .strip("._")
            or "resume"
        )
        return f"{stem}{suffix}"

    @staticmethod
    def _media_type(extension: str) -> str:
        if extension == "pdf":
            return "application/pdf"
        return (
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        )
