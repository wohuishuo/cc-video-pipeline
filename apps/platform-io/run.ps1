param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
& (Join-Path $root "video-platform.ps1") @Arguments
exit $LASTEXITCODE
