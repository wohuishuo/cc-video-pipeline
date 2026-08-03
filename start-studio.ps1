param(
    [int]$Port = 8765,
    [string]$DataRoot = (Join-Path $env:LOCALAPPDATA "VideoGraphStudio"),
    [switch]$NoBrowser,
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"
$repository = $PSScriptRoot

function Resolve-MainRoot {
    $git = Get-Command git -ErrorAction SilentlyContinue
    if (-not $git) { return $repository }
    $common = (& $git.Source -C $repository rev-parse --git-common-dir 2>$null).Trim()
    if (-not $common) { return $repository }
    $resolved = if ([IO.Path]::IsPathRooted($common)) {
        (Resolve-Path -LiteralPath $common).Path
    } else {
        (Resolve-Path -LiteralPath (Join-Path $repository $common)).Path
    }
    return (Split-Path -Parent $resolved)
}

$mainRoot = Resolve-MainRoot
$venv = Join-Path $mainRoot "tools\.venv"
$python = Join-Path $venv "Scripts\python.exe"
$requiredCommands = @("git", "ffmpeg", "ffprobe")
$requiredImports = @("edge_tts", "faster_whisper", "transformers", "torch", "sentencepiece")

function Test-Import([string]$name) {
    if (-not (Test-Path -LiteralPath $python)) { return $false }
    & $python -c "import $name" 2>$null
    return $LASTEXITCODE -eq 0
}

$commandFacts = @($requiredCommands | ForEach-Object {
    $found = Get-Command $_ -ErrorAction SilentlyContinue
    [ordered]@{ name = $_; ready = [bool]$found; path = if ($found) { $found.Source } else { $null } }
})
$importFacts = @($requiredImports | ForEach-Object {
    [ordered]@{ name = $_; ready = (Test-Import $_) }
})

if ($VerifyOnly) {
    $ready = (Test-Path -LiteralPath $python) -and -not ($commandFacts.ready -contains $false) -and -not ($importFacts.ready -contains $false)
    [ordered]@{
        resultClass = if ($ready) { "COMPLETED" } else { "REJECTED_DEPENDENCY" }
        python = $python
        commands = $commandFacts
        imports = $importFacts
        dataRoot = [IO.Path]::GetFullPath($DataRoot)
    } | ConvertTo-Json -Depth 5
    if (-not $ready) { exit 1 }
    exit 0
}

foreach ($fact in $commandFacts) {
    if (-not $fact.ready) {
        throw "Missing required command '$($fact.name)'. Install Git and FFmpeg, then run start-studio.cmd again."
    }
}

if (-not (Test-Path -LiteralPath $python)) {
    $systemPython = Get-Command python -ErrorAction SilentlyContinue
    if (-not $systemPython) { throw "Python 3.12 or newer is required." }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $venv) | Out-Null
    & $systemPython.Source -m venv $venv
}

$missing = @($requiredImports | Where-Object { -not (Test-Import $_) })
if ($missing.Count -gt 0) {
    Write-Host "Installing missing Studio runtime packages: $($missing -join ', ')" -ForegroundColor Cyan
    & $python -m pip install --upgrade pip
    & $python -m pip install edge-tts faster-whisper transformers torch sentencepiece yt-dlp
}

$env:PATH = "$(Join-Path $venv 'Scripts');$env:PATH"
$arguments = @("-Port", $Port, "-DataRoot", $DataRoot)
if ($NoBrowser) { $arguments += "-NoBrowser" }
& (Join-Path $repository "apps\video-graph-studio\run.ps1") @arguments
exit $LASTEXITCODE
