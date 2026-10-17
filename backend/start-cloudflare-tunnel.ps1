$ErrorActionPreference = "Stop"

$cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cloudflared) {
    throw "cloudflared is not installed. Install it, then run this script again."
}

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/health" -TimeoutSec 10
    Write-Host "Backend status: $($health.status)"
} catch {
    throw "The backend is not responding on port 5000. Run .\start-local-demo.ps1 in another terminal first."
}

Write-Host "Starting a temporary public tunnel. Copy the HTTPS URL shown below."
& $cloudflared.Source tunnel --url http://127.0.0.1:5000
