param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
& $python (Join-Path $root ".claude\skills\localize-video\scripts\tts_dub.py") @Arguments
exit $LASTEXITCODE
