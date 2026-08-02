param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
$ErrorActionPreference = "Stop"
$repository = $PSScriptRoot
$gitCommon = (& git -C $repository rev-parse --git-common-dir).Trim()
if ([IO.Path]::IsPathRooted($gitCommon)) {
  $commonPath = (Resolve-Path -LiteralPath $gitCommon).Path
} else {
  $commonPath = (Resolve-Path -LiteralPath (Join-Path $repository $gitCommon)).Path
}
$mainRoot = Split-Path -Parent $commonPath
$python = Join-Path $mainRoot "tools\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
  $python = Join-Path $repository ".venv\Scripts\python.exe"
}
if (-not (Test-Path -LiteralPath $python)) {
  throw "Repository Python runtime not found. Run the project installer first."
}

$previousPythonPath = $env:PYTHONPATH
$previousPythonUtf8 = $env:PYTHONUTF8
$exitCode = 1
Push-Location -LiteralPath $repository
try {
  $env:PYTHONPATH = $repository
  $env:PYTHONUTF8 = "1"
  & $python -m video_platform @Arguments
  $exitCode = $LASTEXITCODE
} finally {
  Pop-Location
  $env:PYTHONPATH = $previousPythonPath
  $env:PYTHONUTF8 = $previousPythonUtf8
}
exit $exitCode
