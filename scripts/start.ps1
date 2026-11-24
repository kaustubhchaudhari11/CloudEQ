# FORGE SPAN: use this checkout and its .env, or report an already-running dashboard.
# Usage (from the repository root):  powershell -ExecutionPolicy Bypass -File scripts\start.ps1
param([ValidateRange(1, 65535)][int]$Port = 8000)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$localUrl = "http://localhost:$Port"
$existingServer = $null
try {
    $existingServer = Invoke-RestMethod -Uri "$localUrl/health" -TimeoutSec 5
} catch {
    # No healthy service was found; the server will report any port-binding error.
}
if ($null -ne $existingServer) {
    if ($existingServer.service -ne 'FORGE SPAN') {
        throw "Another application is using port $Port. Choose another -Port."
    }
    Write-Host "FORGE SPAN is already running at $localUrl" -ForegroundColor Green
    Write-Host ("Execution: {0}; agents: {1}" -f $existingServer.execution_mode, $existingServer.stage_client)
    Write-Host 'For live agents, select Part 2. Part 1 presets use templates.'
    Write-Host 'Restart the existing server if you changed its .env settings.'
    exit 0
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv is not installed. Install it with:" -ForegroundColor Yellow
    Write-Host '  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"'
    exit 1
}
if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
    Write-Host 'Created .env with offline defaults. Follow README section 5 for live agents.'
}
uv sync --locked --all-extras
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Project folder: $(Get-Location)"
Write-Host 'Using local .env settings; existing process variables still take precedence.'
Write-Host "`nOpen $localUrl. Press Ctrl+C to stop.`n" -ForegroundColor Green
uv run --locked --all-extras cloudeq-server --host 127.0.0.1 --port $Port
exit $LASTEXITCODE
