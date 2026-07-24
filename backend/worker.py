from __future__ import annotations

import argparse
import logging
import os
import socket
import time
import uuid

from backend.application.container import ApplicationContainer
from backend.application.jobs.runner import JobRunner
from backend.core.settings import Settings


def main() -> int:
    parser = argparse.ArgumentParser(description="JobHunter durable background worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process at most one available job and exit",
    )
    arguments = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = Settings.from_environment()
    container = ApplicationContainer(settings)
    container.initialize()
    worker_id = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
    runner = JobRunner(
        container.job_queue,
        container.jobs.execute,
        worker_id=worker_id,
        lease_seconds=settings.job_lease_seconds,
        heartbeat_seconds=settings.job_heartbeat_seconds,
    )
    try:
        if arguments.once:
            runner.run_once()
            return 0
        while True:
            if not runner.run_once():
                time.sleep(settings.job_poll_seconds)
    except KeyboardInterrupt:
        return 0
    finally:
        container.close()


if __name__ == "__main__":
    raise SystemExit(main())
