# FORGE SPAN application image (API, dashboard, Plane 4 pipeline).
# Build context is the repository root:  docker compose build app
# Plane 3 sandbox containers are NOT started from inside this image: it has no
# Docker socket. Real container execution is run from the host (see README).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

RUN pip install --no-cache-dir "uv>=0.5"

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --no-dev --extra kafka --extra mongo

RUN useradd --create-home --uid 10001 forge && mkdir -p /data && chown forge /data
USER forge
ENV CLOUDEQ_RUNS_FILE=/data/runs.jsonl \
    CLOUDEQ_OBSERVABILITY_SQLITE_PATH=/data/observability.sqlite3

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"
CMD ["cloudeq-server", "--host", "0.0.0.0", "--port", "8000"]
