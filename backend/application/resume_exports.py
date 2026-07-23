from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.documents import build_resume_docx, build_resume_pdf
from backend.documents.conversion import convert_pdf_to_word, convert_word_to_pdf

from .resume_blobs import ResumeBlobModule


@dataclass(frozen=True)
class ResumeExport:
    path: Path
    filename: str
    media_type: str


class ResumeExportModule:
    """Render or convert an owned resume without exposing its blob adapter."""

    def __init__(self, blobs: ResumeBlobModule, export_folder: str | Path):
        self._blobs = blobs
        self._export_folder = Path(export_folder)

    def export(self, row: dict[str, Any], format_type: str) -> ResumeExport:
        normalized = format_type.lower()
        if normalized not in {"pdf", "word", "docx"}:
            raise ValueError("仅支持 PDF 或 Word 导出")
        extension = "pdf" if normalized == "pdf" else "docx"
        filename = self._safe_filename(row["title"], f".{extension}")
        self._export_folder.mkdir(parents=True, exist_ok=True)
        output_path = self._export_folder / f"{uuid.uuid4().hex}_{filename}"
        original_token = row["file_path"]
        original_type = str(row["file_type"] or "").lower()

        if original_token and self._copy_or_convert(
            original_token,
            original_type,
            extension,
            output_path,
        ):
            return ResumeExport(output_path, filename, self._media_type(extension))
        if extension == "pdf":
            build_resume_pdf(row, output_path)
        else:
            build_resume_docx(row, output_path)
        return ResumeExport(output_path, filename, self._media_type(extension))

    def _copy_or_convert(
        self,
        original_token: str,
        original_type: str,
        extension: str,
        output_path: Path,
    ) -> bool:
        if extension == original_type or (
            extension == "docx" and original_type == "word"
        ):
            self._blobs.copy_to(original_token, output_path)
            return True
        with self._blobs.materialize(
            original_token,
            suffix=f".{original_type or 'bin'}",
        ) as original:
            if extension == "pdf" and original_type in {"doc", "docx"}:
                return convert_word_to_pdf(original, output_path)
            if extension == "docx" and original_type == "pdf":
                try:
                    convert_pdf_to_word(original, output_path)
                except Exception:
                    return False
                return True
        return False

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
