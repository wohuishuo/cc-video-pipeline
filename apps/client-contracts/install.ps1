$ErrorActionPreference="Stop"
if(-not (Get-Command python -ErrorAction SilentlyContinue)){throw "Python 3.12 or newer is required."}
Write-Host "Client Contracts is ready (standard library only)." -ForegroundColor Green
