param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
& (Join-Path $root ".claude\skills\ref-analyze\scripts\extract_frames.ps1") @Arguments
exit $LASTEXITCODE
