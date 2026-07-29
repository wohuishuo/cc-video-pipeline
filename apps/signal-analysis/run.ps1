param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
& (Join-Path $root ".claude\skills\ref-analyze\scripts\probe.ps1") @Arguments
exit $LASTEXITCODE
