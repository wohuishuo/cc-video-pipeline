param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
$ErrorActionPreference = "Stop"
$repository = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$gitCommon = (& git -C $repository rev-parse --git-common-dir).Trim()
$commonPath = if ([IO.Path]::IsPathRooted($gitCommon)) { (Resolve-Path $gitCommon).Path } else { (Resolve-Path (Join-Path $repository $gitCommon)).Path }
$python = Join-Path (Split-Path -Parent $commonPath) "tools\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "Repository Python runtime not found: $python" }
$env:PYTHONPATH = $PSScriptRoot
$env:PYTHONUTF8 = "1"
& $python -m localization_app.cli @Arguments
exit $LASTEXITCODE
