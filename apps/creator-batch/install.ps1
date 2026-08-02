$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "run.ps1") doctor --json
exit $LASTEXITCODE
