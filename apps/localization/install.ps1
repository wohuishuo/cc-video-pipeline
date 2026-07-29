$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$venv = Join-Path $root ".venv"
if (-not (Test-Path $venv)) { python -m venv $venv }
& (Join-Path $venv "Scripts\python.exe") -m pip install edge-tts
