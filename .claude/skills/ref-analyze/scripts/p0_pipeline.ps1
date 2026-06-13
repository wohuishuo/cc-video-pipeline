<#
.SYNOPSIS
  一键 P0 参考视频全流程：下载 → 转录 → 探针 → 抽帧 → 报告。
  把之前 4 步串成一条命令。
.EXAMPLE
  .\p0_pipeline.ps1 -Url "https://www.bilibili.com/video/BVxxxx" -Slug "测试-某up主" -Lang zh
  .\p0_pipeline.ps1 -Url "https://www.bilibili.com/video/BVxxxx" -Slug "测试-某up主" -SkipDownload -SkipTranscribe
#>
param(
  [Parameter(Mandatory = $true)][string]$Url,
  [Parameter(Mandatory = $true)][string]$Slug,
  [string]$Lang = "auto",
  [switch]$SkipDownload,
  [switch]$SkipTranscribe,
  [switch]$SkipProbe,
  [switch]$SkipFrames,
  [int]$MaxFrames = 120,
  [int]$MaxHeight = 1080,
  [string]$Root = "C:\Users\艾莉\Videos\cc视频剪辑"
)
$ErrorActionPreference = "Stop"
$RootPath = Resolve-Path $Root
$skillDir = Join-Path $RootPath ".claude\skills\ref-analyze\scripts"
$py    = Join-Path $RootPath "tools\.venv\Scripts\python.exe"
$slugDir = Join-Path $RootPath "reference\$Slug"

Write-Host "========== P0 Pipeline: $Slug ==========" -ForegroundColor Cyan

# ── Step 1: 下载 ──
if (-not $SkipDownload) {
  Write-Host "`n── Step 1/4: 下载视频 ──" -ForegroundColor Yellow
  & "$skillDir\fetch.ps1" -Url $Url -Slug $Slug -Root $Root -MaxHeight $MaxHeight
  if ($LASTEXITCODE -ne 0) { throw "Step 1 失败" }
} else {
  Write-Host "`n── Step 1/4: 跳过下载 ──" -ForegroundColor DarkGray
}

# ── Step 2: 转录 ──
if (-not $SkipTranscribe) {
  Write-Host "`n── Step 2/4: 语音转文字 (lang=$Lang) ──" -ForegroundColor Yellow
  $audio = Join-Path $slugDir "audio.wav"
  if (-not (Test-Path $audio)) {
    Write-Host "[warn] audio.wav 不存在，尝试从视频提取…" -ForegroundColor Yellow
    $video = Get-ChildItem "$slugDir\video.*" | Where-Object { $_.Extension -in ".mp4",".mkv",".webm" } | Select-Object -First 1
    if ($video) {
      ffmpeg -y -i $video.FullName -vn -ac 1 -ar 16000 $audio 2>$null
    }
  }
  if (Test-Path $audio) {
    & $py (Join-Path $RootPath "tools\transcribe_dispatch.py") $audio --lang $Lang --outdir $slugDir
    if ($LASTEXITCODE -ne 0) { throw "Step 2 失败" }
  } else {
    Write-Host "[warn] 无音频可转录" -ForegroundColor Yellow
  }
} else {
  Write-Host "`n── Step 2/4: 跳过转录 ──" -ForegroundColor DarkGray
}

# ── Step 3: 探针 + 抽帧 ──
if (-not $SkipProbe) {
  Write-Host "`n── Step 3/4: 信号提取（镜头+响度）──" -ForegroundColor Yellow
  & "$skillDir\probe.ps1" -Dir $slugDir
  if ($LASTEXITCODE -ne 0) { Write-Host "[warn] probe 非致命失败" -ForegroundColor Yellow }
}
if (-not $SkipFrames) {
  Write-Host "`n── Step 3/4: 抽帧 ──" -ForegroundColor Yellow
  $video = Get-ChildItem "$slugDir\video.*" | Where-Object { $_.Extension -in ".mp4",".mkv",".webm" } | Select-Object -First 1
  if ($video) {
    $cutsFile = Join-Path $slugDir "cuts.txt"
    $cutsArg = if (Test-Path $cutsFile) { $cutsFile } else { "" }
    & "$skillDir\extract_frames.ps1" -Video $video.FullName -OutDir "$slugDir\frames" -Cuts $cutsArg -MaxFrames $MaxFrames
  }
}

# ── Step 4: 汇总提示 ──
Write-Host "`n========== P0 Pipeline 完成 ==========" -ForegroundColor Cyan
Write-Host "产物位置: $slugDir" -ForegroundColor Green
Write-Host ""
Write-Host "产物清单:" -ForegroundColor White
Get-ChildItem $slugDir -Recurse -File | ForEach-Object {
  $rel = $_.FullName.Replace($slugDir, "").TrimStart("\")
  Write-Host "  $rel ($([math]::Round($_.Length/1KB,1))KB)"
}
Write-Host ""
Write-Host "下一步：让 Claude 读取这些产物写 analysis.md" -ForegroundColor Cyan
Write-Host "  audio.json + cuts.txt + rms.txt + *.info.json + frames/*.jpg" -ForegroundColor DarkGray
