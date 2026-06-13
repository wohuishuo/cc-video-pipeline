<#
.SYNOPSIS
  下载参考视频（yt-dlp），输出到 reference/<slug>/。
  支持 Edge 浏览器 cookie 自动导入（无需手动导出 cookies.txt）。
.EXAMPLE
  .\fetch.ps1 -Url "https://www.bilibili.com/video/BVxxxx" -Slug "up主-选题名"
.EXAMPLE
  .\fetch.ps1 -Url "https://www.bilibili.com/video/BVxxxx" -Slug "up主-选题名" -Browser edge -CookieProfile "Profile 1"
#>
param(
  [Parameter(Mandatory = $true)][string]$Url,
  [Parameter(Mandatory = $true)][string]$Slug,
  [string]$Root = "C:\Users\艾莉\Videos\cc视频剪辑",
  [string]$Browser = "edge",
  [string]$CookieProfile = "",
  [int]$MaxHeight = 1080   # 分析 SOP 用 480 就够，下载快很多；要精修素材再用 1080
)
$ErrorActionPreference = "Stop"
$dir = Join-Path $Root "reference\$Slug"
New-Item -ItemType Directory -Force $dir | Out-Null

# Node 作为 yt-dlp 的 JS runtime（B站/抖音的签名需要）
$node = (Get-Command node -ErrorAction SilentlyContinue).Source

Write-Host "[*] 下载到 $dir"

# B站：优先使用浏览器 cookie（否则只能下低清）
# Edge 的 cookie 数据库被浏览器锁定，yt-dlp 无法直接读（报"Could not copy Chrome cookie database"）。
# 解决方法：Edge 安装扩展 "Get cookies.txt LOCALLY" → 导出 cookies.txt → 放这里自动用
$browserArg = ""
$cookieFile = Join-Path $dir ".." "cookies.txt"
if ($Url -match "bilibili") {
  if (Test-Path $cookieFile) {
    Write-Host "[*] 使用 cookies.txt"
    $browserArg = $cookieFile
  } else {
    Write-Host "[warn] B站需要登录 cookie。解决方法：" -ForegroundColor Yellow
    Write-Host "  1. Edge 安装扩展 'Get cookies.txt LOCALLY'" -ForegroundColor Yellow
    Write-Host "  2. 打开 bilibili.com 并登录" -ForegroundColor Yellow
    Write-Host "  3. 点扩展 → Export As → 保存到 reference\cookies.txt" -ForegroundColor Yellow
    Write-Host "  4. 重新运行此脚本" -ForegroundColor Yellow
    Write-Host "（暂时尝试无 cookie 下载，可能只能拿到低清或失败）" -ForegroundColor Yellow
  }
}

# 画质排序：优先 AVC 编码（hevc/avc > av01），B站默认列表末尾的 av01 画质反而差
# 参考 yt-dlp#12476 B站 4K / yt-dlp#12492 B站 cookie 缺失时格式不全
# 下载器选择：B站对单连接限速（掉到几KB/s）。
#   ⚠️ 不用 aria2c —— 实测它在 B站会【静默截断】音/视频流（报成功但只下了一部分），
#      表现为音频比画面短一截、转录半途而止。改用 yt-dlp 原生下载器 + 大分块请求，
#      既绕过按连接的限速，又不会截断（原生下载器校验 Content-Length）。
$qualityArgs = @(
  "--format-sort", "+vcodec:avc",
  "-f", "bv*[height<=$MaxHeight]+ba/b[height<=$MaxHeight]/bv*+ba/b",
  "--merge-output-format", "mp4",
  "-o", "$dir\video.%(ext)s",
  "--write-info-json",
  "--write-thumbnail",
  "--no-playlist",
  "--http-chunk-size", "10M",       # 每块独立请求，规避按连接限速
  "--concurrent-fragments", "16",
  "--retries", "10", "--fragment-retries", "10"
)

$cookiesArgs = @()
if ($browserArg -and (Test-Path $browserArg)) {
  # 使用手动导出的 cookies.txt
  $cookiesArgs = @("--cookies", $browserArg)
}

$runtimeArgs = @()
if ($node) { $runtimeArgs = @("--js-runtimes", "node") }

$allArgs = $qualityArgs + $cookiesArgs + $runtimeArgs + $Url
Write-Host "[*] yt-dlp $allArgs"
yt-dlp @allArgs
if ($LASTEXITCODE -ne 0) {
  if ($browserArg -and (Test-Path $browserArg)) {
    Write-Host "[warn] cookie 可能已过期，请重新导出 cookies.txt" -ForegroundColor Yellow
  }
  throw "yt-dlp 失败（退出码 $LASTEXITCODE）"
}

# 提取纯音频给 whisper/funasr（mono 16k，转录最优）
$video = Get-ChildItem "$dir\video.*" | Where-Object { $_.Extension -in ".mp4", ".mkv", ".webm" } | Select-Object -First 1

# 截断校验：音频流时长应 ≈ 视频流时长，否则下载不完整（B站常见）
$vdur = [double](ffprobe -v error -select_streams v:0 -show_entries stream=duration -of default=nw=1:nk=1 $video.FullName)
$adur = [double](ffprobe -v error -select_streams a:0 -show_entries stream=duration -of default=nw=1:nk=1 $video.FullName)
if ($vdur -gt 0 -and $adur -gt 0 -and [math]::Abs($vdur - $adur) -gt 5) {
  Write-Host "[warn] 音视频时长不符（视频 $([int]$vdur)s / 音频 $([int]$adur)s）——下载可能被截断。" -ForegroundColor Yellow
  Write-Host "[warn] 建议重跑本脚本；若反复，检查 cookie 或换网络。" -ForegroundColor Yellow
}
ffmpeg -y -i $video.FullName -vn -ac 1 -ar 16000 "$dir\audio.wav" 2>$null
Write-Host "[ok] video + audio.wav 就绪: $dir"
Write-Output $dir
