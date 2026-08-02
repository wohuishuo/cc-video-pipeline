$ErrorActionPreference = "Stop"
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw "Python 3.12 or newer is required." }
$version = (& $python.Source -c "import sys; print('.'.join(map(str,sys.version_info[:3])))").Trim()
Write-Host "Workspace Storage is ready with Python $version (standard library only)." -ForegroundColor Green
