$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$frontendRoot = Join-Path $projectRoot 'frontend'
$backendRoot = Join-Path $projectRoot 'backend'
$backendPython = Join-Path $backendRoot '.venv/Scripts/python.exe'
$nodeExecutable = (Get-Command node -ErrorAction Stop).Source
$apiPort = 8100
$webPort = 3100

function Wait-ForServer([string] $Url) {
    for ($attempt = 0; $attempt -lt 50; $attempt++) {
        try {
            if ((Invoke-WebRequest -Uri $Url -TimeoutSec 2 -UseBasicParsing).StatusCode -eq 200) { return }
        } catch { Start-Sleep -Milliseconds 200 }
    }
    throw "Local test server did not start: $Url"
}

# Do not accidentally test an unrelated pre-existing server on these ports.
foreach ($port in @($apiPort, $webPort)) {
    $probe = [System.Net.Sockets.TcpClient]::new()
    try {
        $probe.Connect('127.0.0.1', $port)
        throw "Port $port is already in use; stop its server or use a separate test environment."
    } catch [System.Net.Sockets.SocketException] {
        # Connection refusal means the selected port is available.
    } finally { $probe.Dispose() }
}

$environmentNames = @('NEXT_TELEMETRY_DISABLED', 'SAFERETURN_API_ORIGIN', 'SAFERETURN_TEST_API_ORIGIN', 'SAFERETURN_TEST_API_OFFLINE', 'PLAYWRIGHT_EXTERNAL_SERVER')
$savedEnvironment = @{}
foreach ($name in $environmentNames) { $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
$apiProcess = $null
$webProcess = $null
Push-Location $frontendRoot
try {
    $env:NEXT_TELEMETRY_DISABLED = '1'
    $env:SAFERETURN_API_ORIGIN = "http://127.0.0.1:$apiPort"
    $env:SAFERETURN_TEST_API_ORIGIN = $env:SAFERETURN_API_ORIGIN
    $env:SAFERETURN_TEST_API_OFFLINE = $null
    $env:PLAYWRIGHT_EXTERNAL_SERVER = '1'

    $apiProcess = Start-Process -FilePath $backendPython -WorkingDirectory $backendRoot -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', "$apiPort" -WindowStyle Hidden -PassThru
    Wait-ForServer "$env:SAFERETURN_API_ORIGIN/api/v1/health/live"
    $webProcess = Start-Process -FilePath $nodeExecutable -WorkingDirectory $frontendRoot -ArgumentList 'node_modules/next/dist/bin/next', 'start', '--hostname', '127.0.0.1', '--port', "$webPort" -WindowStyle Hidden -PassThru
    Wait-ForServer "http://127.0.0.1:$webPort"

    npm test -- --workers=1
    if ($LASTEXITCODE -ne 0) { throw 'Live frontend/backend checks failed.' }

    # Recheck the same running frontend after its real backend becomes unavailable.
    Stop-Process -Id $apiProcess.Id -ErrorAction Stop
    $apiProcess.WaitForExit()
    $apiProcess = $null
    $env:SAFERETURN_TEST_API_OFFLINE = '1'
    npm test -- tests/api-integration.spec.ts --workers=1
    if ($LASTEXITCODE -ne 0) { throw 'Backend outage checks failed.' }
} finally {
    foreach ($process in @($apiProcess, $webProcess)) {
        if ($null -ne $process) { Stop-Process -Id $process.Id -ErrorAction SilentlyContinue }
    }
    foreach ($name in $environmentNames) { [Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name], 'Process') }
    Pop-Location
}
