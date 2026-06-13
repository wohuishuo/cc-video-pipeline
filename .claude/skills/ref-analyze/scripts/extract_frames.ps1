<#
.SYNOPSIS
  从视频抽取关键帧，供 Claude 做视觉分析（拉片）。
  两种模式：场景切换点抽帧 + 固定间隔抽帧。
.EXAMPLE
  .\extract_frames.ps1 -Video "C:\...\video.mp4" -OutDir "C:\...\frames"
.EXAMPLE
  .\extract_frames.ps1 -Video "C:\...\video.mp4" -OutDir "C:\...\frames" -Interval 5 -Cuts ".\cuts.txt"
.EXAMPLE
  .\extract_frames.ps1 -Video "C:\...\video.mp4" -OutDir "C:\...\frames" -MaxFrames 80
#>
param(
  [Parameter(Mandatory = $true)][string]$Video,
  [Parameter(Mandatory = $true)][string]$OutDir,
  [double]$Interval = 5,
  [string]$Cuts,
  [int]$MaxFrames = 120,
  [int]$Width = 720
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $Video)) { throw "Video not found: $Video" }
New-Item -ItemType Directory -Force $OutDir | Out-Null

# 先算视频时长，估算会抽多少帧
$dur_raw = & ffmpeg -i $Video 2>&1 | Select-String "Duration: ([0-9:.]+)"
$dur = 0
if ($dur_raw -match "Duration: (\d+):(\d+):(\d+\.?\d*)") {
  $dur = [double]$Matches[1] * 3600 + [double]$Matches[2] * 60 + [double]$Matches[3]
}
$est_frames = [math]::Ceiling($dur / $Interval)
Write-Host "[*] 时长=${dur}s，按${Interval}s 间隔约抽 $est_frames 帧（上限 $MaxFrames）"

# 自适应间隔：如果预估超上限，拉大间隔
$actual_interval = $Interval
if ($est_frames -gt $MaxFrames) {
  $actual_interval = [math]::Max(1.0, $dur / $MaxFrames)
  Write-Host "[*] 自适应间隔: ${actual_interval}s（防止超 $MaxFrames 帧）"
}

# 1) 固定间隔抽帧
Write-Host "[*] 固定间隔抽帧（${actual_interval}s）…"
$fps = [math]::Max(0.05, 1.0 / $actual_interval)
ffmpeg -y -i $Video -vf "fps=${fps},scale=${Width}:-1" -q:v 5 "$OutDir\grid_%05d.jpg" 2>$null
$grid_count = (Get-ChildItem "$OutDir\grid_*.jpg" -ErrorAction SilentlyContinue).Count
Write-Host "[ok] 间隔抽帧: $grid_count 张 -> grid_XXXXX.jpg"

# 2) 场景切换点附近抽帧（取切换点前后各 1 帧）
$cut_count = 0
if ($Cuts -and (Test-Path $Cuts)) {
  Write-Host "[*] 切镜点抽帧…"
  $cut_times = Get-Content $Cuts | ForEach-Object { [double]$_ }
  $idx = 0
  foreach ($t in $cut_times) {
    if ($idx -ge $MaxFrames) { Write-Host "[*] 切镜帧达上限 $MaxFrames，停止"; break }
    # 切换点前 0.1s
    $pre = [math]::Max(0, $t - 0.1)
    $pad = $idx.ToString("00000")
    ffmpeg -y -ss $pre -i $Video -frames:v 1 -vf "scale=${Width}:-1" -q:v 5 "$OutDir\cut_${pad}_a.jpg" 2>$null
    $idx++
    # 切换点后 0.1s
    if ($idx -lt $MaxFrames) {
      $post = $t + 0.1
      ffmpeg -y -ss $post -i $Video -frames:v 1 -vf "scale=${Width}:-1" -q:v 5 "$OutDir\cut_${pad}_b.jpg" 2>$null
      $idx++
    }
  }
  $cut_count = (Get-ChildItem "$OutDir\cut_*.jpg" -ErrorAction SilentlyContinue).Count
  Write-Host "[ok] 切镜点抽帧: $cut_count 张 -> cut_XXXXX.jpg"
}

$total = $grid_count + $cut_count
Write-Host "[ok] 共 $total 帧 -> $OutDir"
