$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$venv = Join-Path $root ".venv"
if (-not (Test-Path $venv)) { python -m venv $venv }
Write-Output "Select and install a documented engine from tools/tts-mvp/README.md. Model downloads are intentionally not automatic."
