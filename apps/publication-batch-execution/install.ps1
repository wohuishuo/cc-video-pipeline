$ErrorActionPreference = "Stop"
$repository = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
& (Join-Path $PSScriptRoot "run.ps1") doctor --json
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& (Join-Path $repository "apps\publication\install.ps1")
exit $LASTEXITCODE
