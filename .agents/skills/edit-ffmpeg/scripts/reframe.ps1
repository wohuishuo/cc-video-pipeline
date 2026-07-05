<#
.SYNOPSIS
  人脸追踪横转竖（移植自 jianshuo/wjs-reframing-video，改 Intel QSV）。
  裁切窗口跟随「正在说话的人」（靠嘴部开合方差判定 active speaker），
  比 to_vertical.ps1 的模糊/居中裁切更适合多人对谈/采访/播客。
  原视频不会被修改；产出 *_cropped.mp4 + *.crop.json（裁切方案存档）。
.EXAMPLE
  .\reframe.ps1 -Video ".\podcast.mp4"
.EXAMPLE
  .\reframe.ps1 -Video ".\interview.mp4" -Out ".\out_9x16.mp4" -Motion smooth
.NOTES
  依赖 venv 里的 mediapipe + opencv（setup.ps1 会自检）。
  单人/无脸内容用 to_vertical.ps1 即可，不必动用人脸追踪。
#>
param(
  [Parameter(Mandatory = $true)][string]$Video,
  [string]$Out,
  [ValidateSet("auto","portrait","landscape")][string]$Target = "auto",
  [ValidateSet("cut","smooth")][string]$Motion = "cut",
  [ValidateSet("speaker","largest")][string]$FacePick = "speaker",
  [string]$OutputSize = "1080x1920",
  [string]$Encoder = "h264_qsv"
)
$ErrorActionPreference = "Stop"
$root = "C:\Users\艾莉\Videos\cc视频剪辑"
$py = "$root\tools\.venv\Scripts\python.exe"
$script = Join-Path $PSScriptRoot "reframe_crop.py"
if (-not (Test-Path $Video))  { throw "Video not found: $Video" }
if (-not (Test-Path $py))     { throw "venv 不存在，先跑 tools\setup.ps1" }

$argList = @($script, $Video, "--target", $Target, "--motion", $Motion,
  "--face-pick", $FacePick, "--output-size", $OutputSize, "--encoder", $Encoder)
if ($Out) { $argList += @("--out", $Out) }

Write-Host "[*] 人脸追踪裁切（首次运行会下载 ~4MB MediaPipe 模型）…"
& $py @argList
if ($LASTEXITCODE -ne 0) { throw "reframe 失败（退出码 $LASTEXITCODE）" }
Write-Host "[ok] 完成。看裁切日志里的 'face#N: Xs on screen'，若全是 (no face/fallback) 说明没检测到人脸，改用 to_vertical.ps1。"
