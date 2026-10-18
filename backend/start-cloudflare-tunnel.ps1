$ErrorActionPreference = "Stop"

$portableCloudflared = Join-Path $PSScriptRoot "tools\cloudflared.exe"
if (Test-Path -LiteralPath $portableCloudflared) {
    $cloudflaredExe = $portableCloudflared
} else {
    $cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
    if (-not $cloudflared) {
        throw "cloudflared was not found. Put cloudflared.exe in backend\tools or install it system-wide."
    }
    $cloudflaredExe = $cloudflared.Source
}

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/health" -TimeoutSec 10
    Write-Host "Backend status: $($health.status)"
} catch {
    throw "The backend is not responding on port 5000. Run .\start-local-demo.ps1 in another terminal first."
}

Write-Host "Starting a temporary public tunnel. Copy the HTTPS URL shown below."
& $cloudflaredExe tunnel --url http://127.0.0.1:5000
