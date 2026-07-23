from __future__ import annotations

import mimetypes
import re
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any, BinaryIO

from backend.documents import build_resume_pdf
from backend.documents.conversion import convert_pdf_to_word, convert_word_to_pdf
from utils.ai_client import AIClientManager

from .resume_analysis import CAREER_PROFILES
from .training_logic import TrainingLogic


class RuntimeConfigModule:
    """Own runtime-scoped AI configuration and public product catalogs."""

    def __init__(self, ai_clients: AIClientManager, training_logic: TrainingLogic):
        self._ai_clients = ai_clients
        self._training_logic = training_logic

    def providers(self) -> dict[str, Any]:
        client = self._ai_clients.get_ai_client()
        return {
            "success": True,
            "providers": client.available_providers(),
            "active_provider": client.provider.id,
        }

    def configure_ai(self, body: dict[str, Any]) -> dict[str, Any]:
        provider_id = str(body.get("provider") or "glm")
        model_id = str(body.get("model") or body.get("model_id") or "")
        api_key = str(body.get("api_key") or "")
        client = self._ai_clients.set_api_key(api_key, provider_id, model_id)
        return {
            "success": True,
            "provider": client.provider.id,
            "model": client.model,
            "ai_enabled": bool(api_key),
        }

    def ai_status(self) -> dict[str, Any]:
        client = self._ai_clients.get_ai_client()
        return {
            "success": True,
            "ai_enabled": bool(client.api_key),
            "provider": client.provider.id,
            "provider_name": client.provider.name,
            "model": client.model,
            "selected_model": client.model,
            "providers": client.available_providers(),
        }

    @staticmethod
    def career_profiles() -> dict[str, Any]:
        profiles = [
            {
                "id": key,
                "label": profile["label"],
                "interviewer": profile["interviewer"],
                "keywords": profile["keywords"],
            }
            for key, profile in CAREER_PROFILES.items()
        ]
        return {"success": True, "default": "tech", "profiles": profiles}

    def questions(self, category: str) -> dict[str, Any]:
        bank = self._training_logic.question_bank()
        return {"success": True, "data": bank.get(category, bank["general"])}

    @staticmethod
    def test_report(body: dict[str, Any]) -> dict[str, Any]:
        project = str(body.get("project_info") or "AI 求职辅助 Web 系统")
        return {
            "success": True,
            "content": (
                f"## 测试总结报告\n项目：{project}\n\n"
                "### 测试范围\n简历管理、JD 匹配、模拟面试、AI 助手、求职看板。\n\n"
                "### 结论\n核心流程可测，建议继续补充接口自动化、"
                "浏览器兼容性和异常上传用例。"
            ),
            "ai_used": False,
        }


class FileUtilityModule:
    """Own user-file reads and cross-platform document/audio conversion."""

    def __init__(
        self,
        upload_folder: str | Path,
        export_folder: str | Path,
        *,
        max_upload_bytes: int,
    ):
        self._uploads = Path(upload_folder)
        self._exports = Path(export_folder)
        self._max_upload_bytes = int(max_upload_bytes)

    def upload(self, object_key: str) -> tuple[Path, str]:
        source = self._safe_upload(object_key)
        return source, mimetypes.guess_type(source.name)[0] or "application/octet-stream"

    def audio_download(self, object_key: str, format_type: str) -> tuple[Path, str, str]:
        source = self._safe_upload(object_key)
        normalized = (format_type or "original").lower()
        if normalized == "original":
            return source, source.name, self._audio_media_type(source.name)
        if normalized not in {"mp3", "wav"}:
            raise ValueError("Unsupported audio format")
        executable = shutil.which("ffmpeg")
        if not executable:
            raise RuntimeError("当前环境未安装 ffmpeg，无法转码为 MP3/WAV")
        target_name = f"{self._safe_stem(source.stem)}.{normalized}"
        target = self._exports / target_name
        self._exports.mkdir(parents=True, exist_ok=True)
        command = [executable, "-y", "-i", str(source), "-vn"]
        if normalized == "mp3":
            command += ["-codec:a", "libmp3lame", "-b:a", "192k"]
        else:
            command += ["-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2"]
        subprocess.run(command + [str(target)], check=True, capture_output=True)
        return target, target_name, self._audio_media_type(target_name)

    def pdf_to_word(self, source: BinaryIO, filename: str) -> tuple[Path, str]:
        if not filename.lower().endswith(".pdf"):
            raise ValueError("请上传 PDF 文件")
        source_path = self._store_conversion_source(source, filename)
        target_name = f"{self._safe_stem(Path(filename).stem)}.docx"
        target = self._exports / f"{uuid.uuid4().hex}_{target_name}"
        try:
            convert_pdf_to_word(source_path, target)
        finally:
            source_path.unlink(missing_ok=True)
        return target, target_name

    def word_to_pdf(self, source: BinaryIO, filename: str) -> tuple[Path, str]:
        if not filename.lower().endswith((".doc", ".docx")):
            raise ValueError("请上传 Word 文件")
        source_path = self._store_conversion_source(source, filename)
        target_name = f"{self._safe_stem(Path(filename).stem)}.pdf"
        target = self._exports / f"{uuid.uuid4().hex}_{target_name}"
        try:
            if not convert_word_to_pdf(source_path, target):
                from docx import Document

                document = Document(source_path)
                text = "\n".join(
                    paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()
                )
                build_resume_pdf(
                    {"title": Path(filename).stem, "content": text},
                    target,
                )
        finally:
            source_path.unlink(missing_ok=True)
        return target, target_name

    def _safe_upload(self, object_key: str) -> Path:
        root = self._uploads.resolve()
        source = (root / object_key).resolve()
        if source == root or root not in source.parents or not source.is_file():
            raise LookupError("音频文件不存在或已被删除")
        return source

    def _store_conversion_source(self, source: BinaryIO, filename: str) -> Path:
        self._exports.mkdir(parents=True, exist_ok=True)
        suffix = Path(filename).suffix.lower()
        target = self._exports / f".conversion-{uuid.uuid4().hex}{suffix}"
        size = 0
        source.seek(0)
        try:
            with target.open("wb") as destination:
                while chunk := source.read(1024 * 1024):
                    size += len(chunk)
                    if size > self._max_upload_bytes:
                        raise ValueError("上传文件不能超过 20 MB")
                    destination.write(chunk)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return target

    @staticmethod
    def _safe_stem(value: str) -> str:
        return re.sub(r"[^\w\u4e00-\u9fa5.-]+", "_", value).strip("._") or "file"

    @staticmethod
    def _audio_media_type(filename: str) -> str:
        return {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".webm": "audio/webm",
            ".ogg": "audio/ogg",
            ".m4a": "audio/mp4",
        }.get(Path(filename).suffix.lower(), "application/octet-stream")
