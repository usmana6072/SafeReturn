param(
    [ValidateRange(1024, 65535)][int]$Port = 8000,
    [string]$EnvFile
)
$ErrorActionPreference = 'Stop'
$backendRoot = Join-Path (Split-Path $PSScriptRoot -Parent) 'backend'
$python = Join-Path $backendRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Create backend/.venv and install backend dependencies first.' }
$arguments = @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', "$Port")
if ($EnvFile) {
    $resolvedFile = (Resolve-Path -LiteralPath $EnvFile).Path
    $arguments += @('--env-file', $resolvedFile)
}
Push-Location $backendRoot
try {
    Write-Host "API: http://127.0.0.1:$Port/api/v1"
    Write-Host "API explorer: http://127.0.0.1:$Port/docs"
    Write-Host 'No migrations, release-gate changes, seed data or workers are run by this launcher.'
    & $python @arguments
    if ($LASTEXITCODE -ne 0) { throw 'Backend exited unsuccessfully. Check local configuration without sharing secrets.' }
} finally { Pop-Location }
