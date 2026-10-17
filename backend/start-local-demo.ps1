$ErrorActionPreference = "Stop"

$backendDir = $PSScriptRoot
$pythonCandidates = @(
    (Join-Path $backendDir ".venv\Scripts\python.exe"),
    (Join-Path $backendDir "venv\Scripts\python.exe"),
    (Join-Path (Split-Path $backendDir -Parent) ".venv\Scripts\python.exe")
)
$pythonExe = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

if (-not $pythonExe) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python was not found. Create a virtual environment and install backend requirements first."
    }
    $pythonExe = $pythonCommand.Source
}

$env:HOST = "127.0.0.1"
$env:PORT = "5000"
Set-Location -LiteralPath $backendDir
Write-Host "Starting backend at http://127.0.0.1:5000"
& $pythonExe run.py
