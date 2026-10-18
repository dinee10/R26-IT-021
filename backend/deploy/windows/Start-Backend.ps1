[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$backendDirectory = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$candidatePythons = @(
    (Join-Path $backendDirectory '.venv\Scripts\python.exe'),
    (Join-Path $backendDirectory 'venv\Scripts\python.exe')
)
$python = $candidatePythons | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

if (-not $python) {
    throw 'No backend virtual environment was found. Create backend\.venv and install requirements.txt.'
}

Set-Location -LiteralPath $backendDirectory
& $python (Join-Path $backendDirectory 'run.py')
exit $LASTEXITCODE
