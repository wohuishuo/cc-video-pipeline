$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Push-Location (Join-Path $root "tools\remotion-hello")
try { npm install } finally { Pop-Location }
