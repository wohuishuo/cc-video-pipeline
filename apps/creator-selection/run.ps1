param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
$ErrorActionPreference = "Stop"
$repository = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$gitCommon = (& git -C $repository rev-parse --git-common-dir).Trim()
$commonPath = if ([IO.Path]::IsPathRooted($gitCommon)) { (Resolve-Path $gitCommon).Path } else { (Resolve-Path (Join-Path $repository $gitCommon)).Path }
$python = Join-Path (Split-Path -Parent $commonPath) "tools\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "Repository Python 3.12 runtime not found: $python" }
$priorPythonPath = $env:PYTHONPATH
$priorUtf8 = $env:PYTHONUTF8
try {
  $env:PYTHONPATH = "$PSScriptRoot;$repository"
  $env:PYTHONUTF8 = "1"
  Push-Location $repository
  & $python -m creator_selection.cli @Arguments
  exit $LASTEXITCODE
} finally {
  Pop-Location
  $env:PYTHONPATH = $priorPythonPath
  $env:PYTHONUTF8 = $priorUtf8
}
