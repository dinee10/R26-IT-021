param(
    [Parameter(Mandatory = $true)]
    [string]$ApiBaseUrl
)

$ErrorActionPreference = "Stop"
$ApiBaseUrl = $ApiBaseUrl.Trim().TrimEnd('/')

if ($ApiBaseUrl -notmatch '^https?://') {
    throw "ApiBaseUrl must begin with https:// or http://"
}

Set-Location -LiteralPath $PSScriptRoot
flutter pub get
flutter build apk --release --dart-define="API_BASE_URL=$ApiBaseUrl"

$apkPath = Join-Path $PSScriptRoot "build\app\outputs\flutter-apk\app-release.apk"
if (-not (Test-Path -LiteralPath $apkPath)) {
    throw "Flutter finished without creating the expected APK at $apkPath"
}

Write-Host "APK ready: $apkPath"
Write-Host "Backend: $ApiBaseUrl"
