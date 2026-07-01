param(
    [string]$Text = "",
    [string]$InputAudio = "",
    [string]$Out = "",
    [string]$Voice = "zh-CN-XiaoxiaoNeural",
    [int]$Transpose = 0,
    [ValidateSet("dio", "harvest", "parselmouth", "crepe", "crepe-tiny")]
    [string]$F0Method = "dio",
    [switch]$Online
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$edgePy = Join-Path $root "tools\.venv\Scripts\python.exe"
$svcExe = Join-Path $root "tools\tts-mvp\.venv\Scripts\svc.exe"
$base = Join-Path $root "nahida\sovits"
$inputDir = Join-Path $base "input"
$outputDir = Join-Path $base "outputs"
$modelDir = Join-Path $base "logs\44k"
$config = Join-Path $base "configs\44k\config.json"
$mplConfig = Join-Path $base ".mplconfig"

New-Item -ItemType Directory -Force -Path $inputDir, $outputDir, $mplConfig | Out-Null

if (-not (Test-Path $svcExe)) {
    throw "Missing svc.exe. Install with: .\tools\tts-mvp\.venv\Scripts\python.exe -m pip install so-vits-svc-fork"
}
if (-not (Test-Path (Join-Path $modelDir "G_40000.pth"))) {
    throw "Missing Nahida model: $modelDir\G_40000.pth"
}
if (-not (Test-Path $config)) {
    throw "Missing Nahida config: $config"
}

if ($InputAudio) {
    $source = (Resolve-Path $InputAudio).Path
} else {
    if (-not $Text) {
        throw "Provide either -Text or -InputAudio."
    }
    if (-not (Test-Path $edgePy)) {
        throw "Missing edge-tts Python venv: $edgePy"
    }
    $safeName = "source_{0}.mp3" -f (Get-Date -Format "yyyyMMdd_HHmmss")
    $source = Join-Path $inputDir $safeName
    & $edgePy -m edge_tts --voice $Voice --text $Text --write-media $source
    if ($LASTEXITCODE -ne 0) {
        throw "edge-tts failed with exit code $LASTEXITCODE"
    }
}

if (-not $Out) {
    $stem = [IO.Path]::GetFileNameWithoutExtension($source)
    $Out = Join-Path $outputDir "${stem}_nahida.wav"
}
$outPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Out)

$env:MPLCONFIGDIR = (Resolve-Path $mplConfig).Path
if (-not $Online) {
    $env:HF_HUB_OFFLINE = "1"
    $env:TRANSFORMERS_OFFLINE = "1"
}

& $svcExe infer `
    $source `
    --output-path $outPath `
    --speaker nahida `
    --model-path $modelDir `
    --config-path $config `
    --device cpu `
    --f0-method $F0Method `
    --transpose $Transpose `
    --db-thresh -40

if ($LASTEXITCODE -ne 0) {
    throw "svc infer failed with exit code $LASTEXITCODE"
}

Write-Host "[ok] Nahida so-vits output: $outPath"
