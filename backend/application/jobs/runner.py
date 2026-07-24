from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from backend.ports.job_queue import Job, JobQueue

logger = logging.getLogger(__name__)


class JobRunner:
    """Lease one durable job at a time and keep its ownership alive."""

    def __init__(
        self,
        queue: JobQueue,
        executor: Callable[[Job], dict],
        *,
        worker_id: str,
        lease_seconds: int,
        heartbeat_seconds: int,
        retry_delay_seconds: int = 5,
    ):
        self._queue = queue
        self._executor = executor
        self._worker_id = worker_id
        self._lease_seconds = int(lease_seconds)
        self._heartbeat_seconds = int(heartbeat_seconds)
        self._retry_delay_seconds = int(retry_delay_seconds)

    def run_once(self) -> bool:
        job = self._queue.lease(
            self._worker_id,
            lease_seconds=self._lease_seconds,
        )
        if job is None:
            return False
        stop_heartbeat = threading.Event()
        heartbeat = threading.Thread(
            target=self._heartbeat,
            args=(job.id, stop_heartbeat),
            name=f"job-heartbeat-{job.id}",
            daemon=True,
        )
        heartbeat.start()
        try:
            result = self._executor(job)
            if not self._queue.succeed(job.id, self._worker_id, result):
                logger.warning("job %s completed after cancellation or lease loss", job.id)
        except Exception as exc:
            logger.exception("background job %s failed", job.id)
            self._queue.fail(
                job.id,
                self._worker_id,
                str(exc),
                retry_delay_seconds=self._retry_delay_seconds,
            )
        finally:
            stop_heartbeat.set()
            heartbeat.join(timeout=self._heartbeat_seconds + 1)
        return True

    def _heartbeat(self, job_id: str, stopped: threading.Event) -> None:
        while not stopped.wait(self._heartbeat_seconds):
            if not self._queue.heartbeat(
                job_id,
                self._worker_id,
                lease_seconds=self._lease_seconds,
            ):
                return
