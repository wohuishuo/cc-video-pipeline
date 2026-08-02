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
if (-not $python) { $python = (Get-Command python -ErrorAction Stop).Source }
$env:PYTHONPATH = "$PSScriptRoot;$repository"
$env:PYTHONUTF8 = "1"
& $python -m publication_batch.cli @Arguments
exit $LASTEXITCODE
