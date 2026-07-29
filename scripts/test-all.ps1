$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
Push-Location $root
try {
  & $python -m pytest --import-mode=importlib tests\repository tests\research_mvp tests\video_platform -q
  exit $LASTEXITCODE
} finally { Pop-Location }
