# FORGE SPAN: install dependencies and start the dashboard (offline simulation mode).
# Usage (from the repository root):  powershell -ExecutionPolicy Bypass -File scripts\start.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv is not installed. Install it with:" -ForegroundColor Yellow
    Write-Host '  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"'
    exit 1
}
uv sync
Write-Host "`nOpen http://127.0.0.1:8000 in your browser. Press Ctrl+C to stop.`n" -ForegroundColor Green
uv run cloudeq-server
