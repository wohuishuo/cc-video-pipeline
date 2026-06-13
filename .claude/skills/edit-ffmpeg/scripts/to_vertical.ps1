<#
.SYNOPSIS
  横屏 16:9 转竖屏 9:16。
  三种模式：blur（模糊填充背景）| crop（主体居中裁切）| captions（上下留黑加字幕条）。
  走 Intel Arc QSV 硬件编码。
.EXAMPLE
  .\to_vertical.ps1 -Video "C:\...\input.mp4" -Out "C:\...\output_9x16.mp4"
.EXAMPLE
  .\to_vertical.ps1 -Video "C:\...\input.mp4" -Out "C:\...\output_crop.mp4" -Mode crop
.EXAMPLE
  .\to_vertical.ps1 -Video "C:\...\input.mp4" -Out "C:\...\output_cap.mp4" -Mode captions -Subtitle ".\audio.srt"
#>
param(
  [Parameter(Mandatory = $true)][string]$Video,
  [Parameter(Mandatory = $true)][string]$Out,
  [ValidateSet("blur","crop","captions")][string]$Mode = "blur",
  [string]$Subtitle,
  [ValidateSet("h264_qsv","hevc_qsv")][string]$Encoder = "h264_qsv"
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $Video)) { throw "Video not found: $Video" }

# 先探测原始分辨率
$probe = & ffmpeg -i $Video 2>&1 | Select-String "Stream.*Video.* (\d+)x(\d+)"
if (-not ($probe -match "(\d+)x(\d+)")) { throw "无法解析视频分辨率" }
$w = [int]$Matches[1]; $h = [int]$Matches[2]
Write-Host "[*] 原始分辨率: ${w}x${h}"

# 竖屏目标：1080x1920（9:16）
$target_w = 1080
$target_h = 1920

switch ($Mode) {
  "blur" {
    Write-Host "[*] 模式: 模糊填充背景"
    # 先缩放至目标宽度1080，上下填充模糊背景
    $filter = "split[orig][bg];[bg]scale=$($target_w):-2,boxblur=20:20[blurred];[orig]scale=$($target_w):-2[fg];[blurred][fg]overlay=(W-w)/2:(H-h)/2"
  }
  "crop" {
    Write-Host "[*] 模式: 主体居中裁切"
    # 缩放至宽度1080，居中裁切1920高
    $filter = "scale=$($target_w):-2,crop=$($target_w):$($target_h):0:(ih-oh)/2"
  }
  "captions" {
    Write-Host "[*] 模式: 上下留黑加字幕"
    if ($Subtitle -and (Test-Path $Subtitle)) {
      # Windows: ffmpeg filtergraph 里路径中的 `:` 会被当成选项分隔符（如 C:\...）
      # 将反斜杠转成正斜杠，用 subtitles=filename='...' 格式解决
      $safeSub = $Subtitle.Replace('\', '/')
      $filter = "scale=$($target_w):-2,pad=$($target_w):$($target_h):0:(oh-ih)/2:black,setsar=1,subtitles=filename='$safeSub':force_style='FontSize=18,Alignment=2'"
    } else {
      $filter = "scale=$($target_w):-2,pad=$($target_w):$($target_h):0:(oh-ih)/2:black,setsar=1"
    }
  }
}

Write-Host "[*] 编码: $Encoder（Intel QSV）"
ffmpeg -y -i $Video -vf $filter -c:v $Encoder -preset medium -b:v 5M -c:a aac -b:a 128k $Out 2>$null

if ($LASTEXITCODE -eq 0) {
  Write-Host "[ok] 竖屏导出完成 -> $Out"
} else {
  # QSV 失败？退到 CPU 编码
  Write-Host "[warn] QSV 失败，退到 CPU 编码 (libx264)"
  ffmpeg -y -i $Video -vf $filter -c:v libx264 -crf 23 -c:a aac -b:a 128k $Out 2>$null
  if ($LASTEXITCODE -eq 0) { Write-Host "[ok] CPU 编码完成 -> $Out" }
  else { throw "转码失败" }
}
