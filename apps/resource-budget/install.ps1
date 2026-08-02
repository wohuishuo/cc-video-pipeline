$ErrorActionPreference = "Stop"
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw "Python 3.12 or newer is required." }
Write-Host "Resource Budget is ready with Python and SQLite." -ForegroundColor Green
