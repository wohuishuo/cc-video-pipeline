param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  $python = (Get-Command python -ErrorAction Stop).Source
}
& $python -m video_platform @Arguments
exit $LASTEXITCODE
