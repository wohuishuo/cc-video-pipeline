param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
$ErrorActionPreference = "Stop"
$repository = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$gitCommon = (& git -C $repository rev-parse --git-common-dir).Trim()
$commonPath = if ([IO.Path]::IsPathRooted($gitCommon)) { (Resolve-Path $gitCommon).Path } else { (Resolve-Path (Join-Path $repository $gitCommon)).Path }
$python = Join-Path (Split-Path -Parent $commonPath) "tools\.venv\Scripts\python.exe"
$env:PYTHONPATH = "$PSScriptRoot;$repository"; $env:PYTHONUTF8 = "1"
& $python -m client_contracts.cli @Arguments
exit $LASTEXITCODE
