param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
$ErrorActionPreference = "Stop"
$repository = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$gitCommon = (& git -C $repository rev-parse --git-common-dir).Trim()
$commonPath = if ([IO.Path]::IsPathRooted($gitCommon)) { (Resolve-Path $gitCommon).Path } else { (Resolve-Path (Join-Path $repository $gitCommon)).Path }
$commonRoot = Split-Path -Parent $commonPath
$python = Join-Path $commonRoot "tools\.venv\Scripts\python.exe"
$qwenRoot = Join-Path $commonRoot "tools\tts-mvp"
if ($Arguments -contains "qwen3") {
    $qwenPython = Join-Path $qwenRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $qwenPython)) {
        $qwenPython = Join-Path $commonRoot "tools\qwen3tts-env\Scripts\python.exe"
    }
    if (-not (Test-Path -LiteralPath $qwenPython)) {
        throw "Qwen3-TTS runtime not found under $commonRoot\tools"
    }
    $python = $qwenPython
}
if (-not (Test-Path -LiteralPath $python)) { throw "Repository Python runtime not found: $python" }
$pythonPaths = @($PSScriptRoot)
if ($Arguments -contains "qwen3") { $pythonPaths += $qwenRoot }
$env:PYTHONPATH = $pythonPaths -join [IO.Path]::PathSeparator
$env:PYTHONUTF8 = "1"
& $python -m voice_rendering_app.cli @Arguments
exit $LASTEXITCODE
