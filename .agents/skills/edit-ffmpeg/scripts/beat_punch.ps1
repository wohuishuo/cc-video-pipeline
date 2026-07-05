<#
.SYNOPSIS
  卡点特效：在音乐重拍(downbeat)做轻微缩放脉冲(zoom punch)。配合 beat_detect.py 用。
.EXAMPLE
  .\beat_punch.ps1 -Video ".\graded.mp4" -Beats ".\clip.beats.json" -Out ".\punch.mp4"
  .\beat_punch.ps1 -Video ".\graded.mp4" -Beats ".\clip.beats.json" -Out ".\punch.mp4" -Amount 0.08 -Use eight
.NOTES
  -Amount 缩放幅度(默认0.06=放大6%)；-Use downbeats(每小节,默认) / eight(每八拍,更克制) / beats(每拍,密集)
  幅度刻意小，避免廉价感。画面 scale-up 再 center-crop 回 1080x1920，不变形。
#>
param(
  [Parameter(Mandatory = $true)][string]$Video,
  [Parameter(Mandatory = $true)][string]$Beats,
  [Parameter(Mandatory = $true)][string]$Out,
  [double]$Amount = 0.06,
  [ValidateSet("downbeats","eight","beats")][string]$Use = "downbeats",
  [double]$Width = 0.12,   # 脉冲半宽(秒)，越小越"顿"
  [ValidateSet("h264_qsv","hevc_qsv")][string]$Encoder = "h264_qsv"
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $Video)) { throw "Video not found: $Video" }
if (-not (Test-Path $Beats)) { throw "Beats json not found: $Beats" }

$b = Get-Content $Beats -Raw | ConvertFrom-Json
$hits = switch ($Use) {
  "downbeats" { $b.downbeats }
  "eight"     { $b.eight_counts }
  "beats"     { $b.beats }
}
if (-not $hits -or $hits.Count -eq 0) { throw "beats json 里没有 $Use" }
# 防表达式过长：最多取 200 个点
if ($hits.Count -gt 200) { $hits = $hits[0..199] }

# 原始分辨率（用 ffprobe，比解析 ffmpeg 输出稳）
$dims = (ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 $Video) -split ','
$w = [int]$dims[0]; $h = [int]$dims[1]
if ($w -le 0 -or $h -le 0) { throw "无法解析分辨率" }

# 脉冲和：每个重拍一个三角脉冲 max(0,1-|t-db|/width)
# 逗号不转义：表达式在 scale 的单引号值里，\, 会进表达式导致 eval 失败
$pulses = ($hits | ForEach-Object { "max(0,1-abs(t-{0:F3})/{1})" -f $_, $Width }) -join "+"
$z = "1+$Amount*($pulses)"
# scale 逐帧放大(eval=frame 支持时间变量 t) → crop 中心裁回原尺寸 = 缩放脉冲
# 注：crop 的宽高只在 init 算一次不能逐帧动，所以缩放必须用 scale
$filter = "scale=w='trunc(iw*($z)/2)*2':h='trunc(ih*($z)/2)*2':eval=frame,crop=${w}:${h},setsar=1,format=yuv420p"

# 逐帧 scale 是 CPU 滤镜，QSV 对它不兼容且无加速意义 → 直接 libx264
Write-Host "[*] 卡点脉冲: $($hits.Count)个$Use点, 幅度$Amount, libx264编码…"
ffmpeg -y -i $Video -vf $filter -c:v libx264 -crf 20 -preset medium -c:a copy $Out 2>$null
if ($LASTEXITCODE -eq 0) { Write-Host "[ok] 卡点版 -> $Out" } else { throw "卡点编码失败（filter=$filter）" }
