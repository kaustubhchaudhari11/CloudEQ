# Sandbox image for FORGE SPAN Plane 3.
# Base: python:3.12-slim. The slim image does not include pytest.
# The only allowlisted test command is `python -m pytest`, so this image adds pytest 9.2.0.
# Build: docker build -t cloudeq-runtime:py3.12-pytest9.2.0 infra/runtime
# Run time network, user, and mounts are set by the executor, not by this file.
FROM python:3.12-slim

RUN pip install --no-cache-dir "pytest==9.2.0"

WORKDIR /workspace
