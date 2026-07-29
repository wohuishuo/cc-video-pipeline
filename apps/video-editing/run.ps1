param([Parameter(Position=0, Mandatory=$true)][ValidateSet("silence-cut","vertical","reframe")][string]$Command,[Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments)
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$scripts = @{"silence-cut"="silence_cut.ps1";"vertical"="to_vertical.ps1";"reframe"="reframe.ps1"}
& (Join-Path $root ".claude\skills\edit-ffmpeg\scripts\$($scripts[$Command])") @Arguments
exit $LASTEXITCODE
