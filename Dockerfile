# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:0.13.3 AS uv
FROM python:3.13-slim-bookworm AS application
COPY --from=uv /uv /uvx /bin/
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY src/ ./src/
COPY --from=frontend /build/frontend/dist ./frontend/dist/
RUN useradd --uid 10001 --create-home app \
    && mkdir -p /data/odm /data/tmp \
    && chown -R app:app /data /app
USER app
ENV PATH="/app/.venv/bin:$PATH" DATABASE_PATH=/data/database.sqlite ODM_DIR=/data/odm TMPDIR=/data/tmp
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*", "--limit-concurrency", "32"]
