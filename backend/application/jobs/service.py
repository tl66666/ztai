from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from backend.application.platform import FileUtilityModule
from backend.application.resume_intelligence import ResumeIntelligenceModule
from backend.ports import BlobStorage
from backend.ports.job_queue import Job, JobQueue


@dataclass(frozen=True)
class JobResult:
    content: bytes
    filename: str
    media_type: str


class JobService:
    """Submit, inspect, cancel, and execute supported durable job types."""

    def __init__(
        self,
        queue: JobQueue,
        storage: BlobStorage,
        resume_intelligence: ResumeIntelligenceModule,
        file_utilities: FileUtilityModule,
        *,
        local_user_id: int,
        max_attempts: int,
    ):
        self._queue = queue
        self._storage = storage
        self._resume_intelligence = resume_intelligence
        self._file_utilities = file_utilities
        self._local_user_id = int(local_user_id)
        self._max_attempts = int(max_attempts)

    def submit_resume_analysis(
        self,
        resume_id: int,
        body: dict[str, Any],
        *,
        owner_id: int,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        self._require_owner(owner_id)
        job = self._queue.submit(
            "resume.analyze",
            {"resume_id": int(resume_id), "body": body},
            owner_id=owner_id,
            idempotency_key=idempotency_key,
            max_attempts=self._max_attempts,
        )
        return self._accepted(job)

    def submit_document_conversion(
        self,
        source: BinaryIO,
        *,
        filename: str,
        target_format: str,
        owner_id: int,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        self._require_owner(owner_id)
        normalized_target = target_format.strip().lower()
        if normalized_target not in {"pdf", "docx"}:
            raise ValueError("target_format must be pdf or docx")
        suffix = Path(filename).suffix.lower()
        if normalized_target == "docx" and suffix != ".pdf":
            raise ValueError("转换为 Word 时请上传 PDF 文件")
        if normalized_target == "pdf" and suffix not in {".doc", ".docx"}:
            raise ValueError("转换为 PDF 时请上传 Word 文件")
        reference = self._storage.store(
            source,
            original_name=filename,
            namespace="job-inputs/document-conversion",
            owner_id=owner_id,
        )
        try:
            job = self._queue.submit(
                "document.convert",
                {
                    "source_blob": reference.to_token(),
                    "filename": filename,
                    "target_format": normalized_target,
                },
                owner_id=owner_id,
                idempotency_key=idempotency_key,
                max_attempts=self._max_attempts,
            )
        except Exception:
            self._storage.delete(reference)
            raise
        if job.payload.get("source_blob") != reference.to_token():
            self._storage.delete(reference)
        return self._accepted(job)

    def status(self, job_id: str, *, owner_id: int) -> tuple[dict[str, Any], int]:
        self._require_owner(owner_id)
        job = self._queue.get(job_id, owner_id=owner_id)
        if job is None:
            return {"success": False, "message": "任务不存在"}, 404
        payload = self._public_job(job)
        return {"success": True, "task": payload}, 200

    def cancel(self, job_id: str, *, owner_id: int) -> tuple[dict[str, Any], int]:
        self._require_owner(owner_id)
        job = self._queue.cancel(job_id, owner_id=owner_id)
        if job is None:
            return {"success": False, "message": "任务不存在"}, 404
        return {"success": True, "task": self._public_job(job)}, 200

    def result(self, job_id: str, *, owner_id: int) -> JobResult:
        self._require_owner(owner_id)
        job = self._queue.get(job_id, owner_id=owner_id)
        if job is None:
            raise LookupError("任务不存在")
        if job.status != "succeeded":
            raise RuntimeError("任务尚未完成")
        result = job.result or {}
        reference_token = result.get("blob_ref")
        if not reference_token:
            raise LookupError("该任务没有可下载文件")
        reference = self._storage.restore(str(reference_token), owner_id=owner_id)
        with self._storage.open(reference) as source:
            content = source.read()
        return JobResult(
            content=content,
            filename=str(result.get("filename") or "result.bin"),
            media_type=str(result.get("media_type") or reference.content_type),
        )

    def execute(self, job: Job) -> dict[str, Any]:
        self._require_owner(job.owner_id)
        if job.job_type == "resume.analyze":
            payload, status_code = self._resume_intelligence.analyze(
                int(job.payload["resume_id"]),
                dict(job.payload.get("body") or {}),
            )
            if status_code >= 400:
                raise ValueError(str(payload.get("message") or "resume analysis failed"))
            return payload
        if job.job_type == "document.convert":
            return self._execute_document_conversion(job)
        raise ValueError(f"unsupported job type: {job.job_type}")

    def _execute_document_conversion(self, job: Job) -> dict[str, Any]:
        payload = job.payload
        source_reference = self._storage.restore(
            str(payload["source_blob"]),
            owner_id=job.owner_id,
        )
        target_format = str(payload["target_format"])
        with self._storage.open(source_reference) as source:
            if target_format == "docx":
                path, filename = self._file_utilities.pdf_to_word(
                    source,
                    str(payload["filename"]),
                )
                media_type = (
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                )
            else:
                path, filename = self._file_utilities.word_to_pdf(
                    source,
                    str(payload["filename"]),
                )
                media_type = "application/pdf"
        try:
            with path.open("rb") as converted:
                result_reference = self._storage.store(
                    converted,
                    original_name=filename,
                    namespace="job-results/document-conversion",
                    owner_id=job.owner_id,
                    content_type=media_type,
                )
        finally:
            path.unlink(missing_ok=True)
        with suppress(Exception):
            self._storage.delete(source_reference)
        return {
            "filename": filename,
            "media_type": media_type,
            "blob_ref": result_reference.to_token(),
            "download_url": f"/api/jobs/{job.id}/result",
        }

    def _require_owner(self, owner_id: int) -> None:
        if int(owner_id) != self._local_user_id:
            raise PermissionError("当前用户不能访问该后台任务")

    @staticmethod
    def _accepted(job: Job) -> dict[str, Any]:
        return {
            "success": True,
            "task_id": job.id,
            "status": job.status,
            "status_url": f"/api/jobs/{job.id}",
        }

    @staticmethod
    def _public_job(job: Job) -> dict[str, Any]:
        result = dict(job.result or {})
        result.pop("blob_ref", None)
        return {
            "id": job.id,
            "type": job.job_type,
            "status": job.status,
            "result": result or None,
            "error": job.error,
            "attempts": job.attempts,
            "max_attempts": job.max_attempts,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }
