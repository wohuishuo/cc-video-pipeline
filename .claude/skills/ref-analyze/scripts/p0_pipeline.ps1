<#
.SYNOPSIS
  P0 全流程：下载→转录→探针→抽帧，带"是否继续"提示。
  每步完成后明确告诉你"做完了"或"做不下去因为 X"，等你说 ok 再下一步。
  死了能断点续传（转录后 audio.srt 存在就跳过）。
.EXAMPLE
  .\p0_pipeline.ps1 -Url "https://www.bilibili.com/video/BVxxx" -Slug "测试-某up主"
  .\p0_pipeline.ps1 -Url "..." -Slug "..." -Lang en       # 外语
  .\p0_pipeline.ps1 -Url "..." -Slug "..." -SkipDownload # 已有视频只跑转录+探针+抽帧
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
  [string]$Root = "C:\Users\艾莉\Videos\cc视频剪辑"
)
$ErrorActionPreference = "Stop"
$RootPath = Resolve-Path $Root
$skillDir = Join-Path $RootPath ".claude\skills\ref-analyze\scripts"
$py    = Join-Path $RootPath "tools\.venv\Scripts\python.exe"
$slugDir = Join-Path $RootPath "reference\$Slug"

function Step($name) {
  Write-Host ""
  Write-Host "═══ $name ═══" -ForegroundColor Cyan
}
function OK($msg)  { Write-Host "  ✅ $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "  ⚠️  $msg" -ForegroundColor Yellow }
function Fail($msg) { Write-Host "  ❌ $msg" -ForegroundColor Red }
function Ask($q) {
  while ($true) {
    Write-Host "  $q [Y/n]" -ForegroundColor Magenta -NoNewline
    $a = Read-Host
    if ([string]::IsNullOrWhiteSpace($a)) { $a = "Y" }
    if ($a -match "^[Yy]") { return $true }
    if ($a -match "^[Nn]") { return $false }
  }
}

# ── 准备目录 ──
New-Item -ItemType Directory -Force $slugDir | Out-Null
Write-Host "📂 项目根: $RootPath" -ForegroundColor DarkGray
Write-Host "📂 输出:   $slugDir" -ForegroundColor DarkGray

# ── Step 1: 下载 ──
if (-not $SkipDownload) {
  Step "Step 1/4: 下载视频"
  $videoMP4 = Get-ChildItem "$slugDir\video.mp4" -ErrorAction SilentlyContinue
  if ($videoMP4) {
    OK "已存在 $([Math]::Round($videoMP4.Length/1MB,1)) MB, 跳过"
  } else {
    & "$skillDir\fetch.ps1" -Url $Url -Slug $Slug -Root $Root
    if ($LASTEXITCODE -ne 0) { Fail "下载失败"; return }
    OK "下载完成"
  }
} else {
  Write-Host "  (跳过 Step 1: 下载)" -ForegroundColor DarkGray
}

# ── Step 2: 转录 ──
if (-not $SkipTranscribe) {
  Step "Step 2/4: 语音转文字 (lang=$Lang)"

  $audioSRT = Join-Path $slugDir "audio.srt"
  if (Test-Path $audioSRT) {
    OK "audio.srt 已存在, 跳过 (断点续传)"
  } else {
    $audioWAV = Join-Path $slugDir "audio.wav"
    if (-not (Test-Path $audioWAV)) {
      $video = Get-ChildItem "$slugDir\video.*" | Where-Object { $_.Extension -in ".mp4", ".mkv", ".webm" } | Select-Object -First 1
      if (-not $video) { Fail "无 video.mp4，请先跑 Step 1"; return }
      Warn "audio.wav 不存在，从视频抽..."
      ffmpeg -y -i $video.FullName -vn -ac 1 -ar 16000 $audioWAV 2>$null
    }

    if (-not (Ask "启动转录？(FunASR SenseVoiceSmall 首次跑会下载 ~200MB 模型)")) { return }
    Write-Host "  ⏳ 转录中（10-20 分钟，看视频长度）..." -ForegroundColor Yellow
    & $py (Join-Path $RootPath "tools\transcribe_dispatch.py") $audioWAV --lang $Lang --outdir $slugDir 2>&1 | Out-String
    if (Test-Path $audioSRT) { OK "转录完成 $([Math]::Round((Get-Item $audioSRT).Length/1KB,1)) KB" }
    else { Fail "转录失败，请看 stderr"; return }
  }
} else {
  Write-Host "  (跳过 Step 2: 转录)" -ForegroundColor DarkGray
}

# ── Step 3: 探针 ──
if (-not $SkipProbe) {
  Step "Step 3/4: 镜头+响度检测"
  $cutsFile = Join-Path $slugDir "cuts.txt"
  if (Test-Path $cutsFile) {
    OK "cuts.txt 已存在, 跳过"
  } else {
    & "$skillDir\probe.ps1" -Dir $slugDir
    if ($LASTEXITCODE -ne 0) { Fail "探针失败"; return }
    OK "探针完成"
  }
} else {
  Write-Host "  (跳过 Step 3: 探针)" -ForegroundColor DarkGray
}

# ── Step 4: 抽帧 ──
if (-not $SkipFrames) {
  Step "Step 4/4: 抽帧"
  $framesDir = Join-Path $slugDir "frames"
  if (Test-Path "$framesDir\grid_00001.jpg") {
    OK "frames/ 已存在, 跳过"
  } else {
    $video = Get-ChildItem "$slugDir\video.*" | Where-Object { $_.Extension -in ".mp4", ".mkv", ".webm" } | Select-Object -First 1
    if (-not $video) { Fail "无 video.mp4"; return }
    $cutsArg = if (Test-Path $cutsFile) { $cutsFile } else { "" }
    & "$skillDir\extract_frames.ps1" -Video $video.FullName -OutDir $framesDir -Cuts $cutsArg -MaxFrames $MaxFrames
    if ($LASTEXITCODE -ne 0) { Fail "抽帧失败"; return }
    OK "抽帧完成"
  }
} else {
  Write-Host "  (跳过 Step 4: 抽帧)" -ForegroundColor DarkGray
}

# ── 汇总 ──
Step "完成"
Write-Host "  产物在 $slugDir" -ForegroundColor Cyan
Get-ChildItem $slugDir -Recurse -File | ForEach-Object {
  $rel = $_.FullName.Replace($slugDir, "").TrimStart("\")
  $kb = [Math]::Round($_.Length/1KB, 1)
  if ($kb -lt 1024) { Write-Host "    $rel ($kb KB)" -ForegroundColor Gray }
  else { Write-Host "    $rel ([Math]::Round($kb/1024,1)) MB)" -ForegroundColor Gray }
}
Write-Host ""
Write-Host "👉 下一步: 让 Claude 读产物写 analysis.md" -ForegroundColor Cyan
Write-Host "   → '读 reference\$Slug\ 下的产物写 analysis.md'" -ForegroundColor Cyan
