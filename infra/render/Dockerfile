FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv PATH="/opt/venv/bin:${PATH}"
RUN pip install --no-cache-dir uv==0.13.6
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --extra render --extra kafka --extra mongo
COPY infra/render/runtime-requirements.txt /opt/runtime-requirements.txt
RUN pip download --only-binary=:all: --python-version 3.11 --implementation cp --abi cp311 \
    --platform manylinux2014_x86_64 --dest /opt/forge-wheels -r /opt/runtime-requirements.txt \
    && pip download --only-binary=:all: --python-version 3.12 --implementation cp --abi cp312 \
    --platform manylinux2014_x86_64 --dest /opt/forge-wheels -r /opt/runtime-requirements.txt
RUN useradd --create-home --uid 10001 forge && mkdir -p /var/data && chown forge /var/data
COPY infra/render/start.py /app/start.py
USER forge
EXPOSE 10000
CMD ["python", "/app/start.py"]
