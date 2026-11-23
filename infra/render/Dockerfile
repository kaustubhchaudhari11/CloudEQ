FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv PATH="/opt/venv/bin:${PATH}"
RUN pip install --no-cache-dir uv==0.13.6
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --extra render --extra kafka --extra mongo
RUN pip download --only-binary=:all: --dest /opt/forge-wheels pytest==9.2.0
RUN useradd --create-home --uid 10001 forge && mkdir -p /var/data && chown forge /var/data
COPY infra/render/start.py /app/start.py
USER forge
EXPOSE 10000
CMD ["python", "/app/start.py"]
