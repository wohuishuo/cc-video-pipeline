<#
.SYNOPSIS
  自动调色（Cos 跳舞向）：提对比/饱和/亮度 + 轻锐化 + 肤色友好。Intel QSV 编码。
.EXAMPLE
  .\color_grade.ps1 -Video ".\in.mp4" -Out ".\out_graded.mp4"
  .\color_grade.ps1 -Video ".\in.mp4" -Out ".\out.mp4" -Strength high
.NOTES
  三档：low(自然) / med(默认,通透) / high(浓郁,适合鲜艳cos服)。
  饱和度刻意不拉太高，避免脸/红色过曝。
#>
param(
  [Parameter(Mandatory = $true)][string]$Video,
  [Parameter(Mandatory = $true)][string]$Out,
  [ValidateSet("low","med","high")][string]$Strength = "med",
  [ValidateSet("h264_qsv","hevc_qsv")][string]$Encoder = "h264_qsv"
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $Video)) { throw "Video not found: $Video" }

# 调色参数三档（eq + unsharp）
switch ($Strength) {
  "low"  { $eq = "contrast=1.04:brightness=0.01:saturation=1.08:gamma=0.99"; $sharp="unsharp=5:5:0.4:5:5:0.0" }
  "med"  { $eq = "contrast=1.09:brightness=0.02:saturation=1.18:gamma=0.97"; $sharp="unsharp=5:5:0.6:5:5:0.0" }
  "high" { $eq = "contrast=1.14:brightness=0.02:saturation=1.30:gamma=0.95"; $sharp="unsharp=7:7:0.8:5:5:0.0" }
}
# setsar 防变形；format 保证兼容
$filter = "eq=$eq,$sharp,setsar=1,format=yuv420p"

Write-Host "[*] 调色($Strength) + QSV 编码…"
ffmpeg -y -i $Video -vf $filter -c:v $Encoder -preset medium -b:v 8M -c:a copy $Out 2>$null
if ($LASTEXITCODE -eq 0) {
  Write-Host "[ok] 调色完成 -> $Out"
} else {
  Write-Host "[warn] QSV 失败，退 CPU libx264"
  ffmpeg -y -i $Video -vf $filter -c:v libx264 -crf 20 -preset medium -c:a copy $Out 2>$null
  if ($LASTEXITCODE -eq 0) { Write-Host "[ok] CPU 编码完成 -> $Out" } else { throw "调色失败" }
}
