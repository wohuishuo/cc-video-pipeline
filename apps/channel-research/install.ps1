$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$venv = Join-Path $root ".venv"
if (-not (Test-Path $venv)) { python -m venv $venv }
Write-Output "Channel Research domain core is ready. Install platform adapters only when needed."
