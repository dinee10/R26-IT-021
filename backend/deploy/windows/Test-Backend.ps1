[CmdletBinding()]
param(
    [string]$BaseUrl = 'http://127.0.0.1:5000'
)

$ErrorActionPreference = 'Stop'
$healthUrl = $BaseUrl.TrimEnd('/') + '/api/health'
$response = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 30

if (-not $response.status) {
    throw "The health endpoint at $healthUrl returned an unexpected response."
}

$response | ConvertTo-Json -Depth 8
