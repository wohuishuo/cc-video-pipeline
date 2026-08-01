$ErrorActionPreference = "Stop"
$repository = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
& (Join-Path $repository "apps\platform-io\install.ps1")
Write-Host "Source Intake is ready." -ForegroundColor Green

