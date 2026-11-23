# FORGE SPAN with the REAL Docker sandbox (Plane 3). Requires Docker Desktop running.
# Builds the sandbox image once, then starts the dashboard in docker execution mode.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
docker info | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "Docker Desktop is not running." -ForegroundColor Red; exit 1 }
docker build -t cloudeq-runtime:py3.12-pytest9.2.0 infra/runtime
uv sync
$env:CLOUDEQ_EXECUTION_MODE = "docker"
Write-Host "`nOpen http://127.0.0.1:8000 (docker mode). Press Ctrl+C to stop.`n" -ForegroundColor Green
uv run cloudeq-server
