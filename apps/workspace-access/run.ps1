param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
$ErrorActionPreference = "Stop"
$repository = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$gitCommon = (& git -C $repository rev-parse --git-common-dir 2>$null)
$python = $null
if ($LASTEXITCODE -eq 0 -and $gitCommon) {
  $commonPath = if ([IO.Path]::IsPathRooted($gitCommon.Trim())) { (Resolve-Path $gitCommon.Trim()).Path } else { (Resolve-Path (Join-Path $repository $gitCommon.Trim())).Path }
  $candidate = Join-Path (Split-Path -Parent $commonPath) "tools\.venv\Scripts\python.exe"
  if (Test-Path -LiteralPath $candidate) { $python = $candidate }
}
if (-not $python) {
  $command = Get-Command python -ErrorAction SilentlyContinue
  if (-not $command) { throw "Python 3.12 or newer is required." }
  $python = $command.Source
}
$env:PYTHONPATH = "$PSScriptRoot;$repository"
$env:PYTHONUTF8 = "1"
& $python -m workspace_access.cli @Arguments
exit $LASTEXITCODE
