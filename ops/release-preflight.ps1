param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("staging", "production")]
    [string]$Environment,
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^https://")]
    [string]$ApiOrigin
)

$ErrorActionPreference = "Stop"

function Test-Endpoint {
    param(
        [string]$Uri,
        [int]$ExpectedStatus
    )

    $response = Invoke-WebRequest -Uri $Uri -Method Get -UseBasicParsing
    if ($response.StatusCode -ne $ExpectedStatus) {
        throw "Unexpected status $($response.StatusCode) from $Uri"
    }
}

Write-Output "Release preflight: $Environment"
Write-Output "Checking public liveness without exposing configuration..."
Test-Endpoint -Uri "$ApiOrigin/api/v1/health/live" -ExpectedStatus 200
Write-Output "Liveness passed."

if (-not $env:SAFERETURN_READINESS_TOKEN) {
    throw "SAFERETURN_READINESS_TOKEN is required for an authorized readiness check."
}

Write-Output "Checking authorized readiness..."
$headers = @{ Authorization = "Bearer $env:SAFERETURN_READINESS_TOKEN" }
$readiness = Invoke-WebRequest -Uri "$ApiOrigin/api/v1/health/ready" -Headers $headers -Method Get -UseBasicParsing
if ($readiness.StatusCode -ne 200) {
    throw "Readiness did not return 200."
}
Write-Output "Readiness passed."
Write-Output "No migrations, writes, provider calls, or deployment actions were performed."
