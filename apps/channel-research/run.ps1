param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
Push-Location $root
try { & $python -m research_mvp @Arguments; exit $LASTEXITCODE } finally { Pop-Location }
