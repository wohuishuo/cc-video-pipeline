<#
.SYNOPSIS
  对参考视频做客观信号提取：镜头切换点 + 音量包络（BGM/语音节奏的代理信号）。
  纯 ffmpeg，无需联网。输出 cuts.txt / loudness.json，供 Claude 分析报告消费。
.EXAMPLE
  .\probe.ps1 -Dir "C:\...\reference\up主-选题名"
#>
param(
  [Parameter(Mandatory = $true)][string]$Dir
)
$ErrorActionPreference = "Stop"
$video = Get-ChildItem "$Dir\video.*" | Where-Object { $_.Extension -in ".mp4", ".mkv", ".webm" } | Select-Object -First 1
if (-not $video) { throw "找不到 video.* in $Dir" }

# 1) 镜头切换检测：scene score > 0.3 视为切换
# 注意 ffmpeg scene 值是当前帧 vs 前一帧的差异 → pts_time 对应的是切换后的帧
# 减半帧时间 (~16ms @30fps) 修正到实际切换点
Write-Host "[*] 镜头切换检测…"
$raw = ffmpeg -i $video.FullName -filter:v "select='gt(scene,0.3)',showinfo" -f null - 2>&1
$cuts = $raw | Select-String -Pattern "pts_time:([0-9.]+)" | ForEach-Object { [double]$_.Matches[0].Groups[1].Value }
# 减一帧 (~0.04s) 修正到实际切镜点
$cuts = $cuts | ForEach-Object { [math]::Max(0, $_ - 0.04) }
$cuts | ForEach-Object { "{0:F2}" -f $_ } | Set-Content "$Dir\cuts.txt"
Write-Host "[ok] 检测到 $($cuts.Count) 个镜头切换 -> cuts.txt"

# 2) 每秒响度（语音/BGM 能量代理），用于找钩子/高潮/留白
Write-Host "[*] 响度包络…"
# ffmpeg ametadata 滤镜的 file= 路径是相对 CWD 解析的，必须用绝对路径
$rmsAbs = Join-Path (Resolve-Path $Dir) "rms.txt"
ffmpeg -i $video.FullName -af "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level:file=`"$rmsAbs`"" -f null - 2>$null
if (Test-Path $rmsAbs) { Write-Host "[ok] rms.txt 就绪 ($rmsAbs)" } else { Write-Host "[warn] rms.txt 未生成" }
Write-Output $Dir
