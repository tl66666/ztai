# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:0.8.17 AS uv

FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        fonts-noto-cjk \
        libreoffice-writer \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN groupadd --gid 10001 jobhunter \
    && useradd --uid 10001 --gid jobhunter --create-home jobhunter \
    && mkdir -p /app/data/uploads /app/data/exports /app/data/runtime \
    && chown -R jobhunter:jobhunter /app/data

USER 10001:10001

ENV JOBHUNTER_PROJECT_ROOT=/app \
    JOBHUNTER_DB_PATH=data/jobhunter.db \
    JOBHUNTER_UPLOAD_FOLDER=data/uploads \
    JOBHUNTER_EXPORT_FOLDER=data/exports \
    JOBHUNTER_AI_CONFIG_PATH=data/runtime/ai-config.json \
    JOBHUNTER_PORT=8000 \
    JOBHUNTER_WORKERS=1

EXPOSE 8000
VOLUME ["/app/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["uv", "run", "--no-sync", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/healthz', timeout=3).read()"]

CMD ["uv", "run", "--no-sync", "python", "-m", "backend.cli"]
