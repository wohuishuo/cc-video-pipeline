<#
.SYNOPSIS
  P0 流水线进度查看器。显示每条参考视频卡在哪一步（下载/转录/探针/抽帧），
  以及当前下载百分比和速度。
.EXAMPLE
  # 看一次
  .\watch.ps1 -Slug "曙光-分享喜讯","商业金融书单"
.EXAMPLE
  # 每 5 秒刷新，直到全部完成
  .\watch.ps1 -Slug "曙光-分享喜讯","商业金融书单" -Loop
#>
param(
  [Parameter(Mandatory = $true)][string[]]$Slug,
  [switch]$Loop,
  [int]$Interval = 5,
  [string]$LogFile,
  [string]$Root = "C:\Users\艾莉\Videos\cc视频剪辑"
)

function Show-Once {
  try { Clear-Host } catch { Write-Host "`n`n" }  # 非交互 shell 里 Clear-Host 会报句柄错，忽略
  Write-Host "═══════ P0 进度  $(Get-Date -Format 'HH:mm:ss') ═══════" -ForegroundColor Cyan
  foreach ($s in $Slug) {
    $d = Join-Path $Root "reference\$s"
    Write-Host "`n▶ $s" -ForegroundColor White
    if (-not (Test-Path $d)) { Write-Host "   未开始" -ForegroundColor DarkGray; continue }

    # 各阶段判定（看产物文件是否就位）
    $hasVideo = (Get-ChildItem "$d\video.*" -Include *.mp4,*.mkv,*.webm -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike "*.part" }).Count -gt 0
    $part     = Get-ChildItem "$d\*.part" -ErrorAction SilentlyContinue | Select-Object -First 1
    $hasAudio = Test-Path "$d\audio.wav"
    $hasSrt   = Test-Path "$d\audio.srt"
    $hasCuts  = Test-Path "$d\cuts.txt"
    $frames   = (Get-ChildItem "$d\frames\*.jpg" -ErrorAction SilentlyContinue).Count

    function Step($ok, $label, $extra="") {
      $mark = if ($ok) { "[✓]" } else { "[ ]" }
      $color = if ($ok) { "Green" } else { "DarkGray" }
      Write-Host ("   {0} {1} {2}" -f $mark, $label, $extra) -ForegroundColor $color
    }
    # 下载阶段：若有 .part，显示百分比
    $dlExtra = ""
    if ($part) {
      $target = $part.Name -replace '\.part$',''
      $dlExtra = "下载中… $([math]::Round($part.Length/1MB,1))MB"
    } elseif ($hasVideo) {
      $v = Get-ChildItem "$d\video.*" -Include *.mp4,*.mkv,*.webm | Select-Object -First 1
      $dlExtra = "$([math]::Round($v.Length/1MB,1))MB"
    }
    Step ($hasVideo) "下载视频" $dlExtra
    Step ($hasSrt)   "语音转文字" $(if($hasSrt){"$((Get-Content "$d\audio.srt" | Measure-Object).Count) 行字幕"})
    Step ($hasCuts)  "镜头/响度探针" $(if($hasCuts){"$((Get-Content "$d\cuts.txt").Count) 个切点"})
    Step ($frames -gt 0) "抽帧" $(if($frames){"$frames 张"})
  }

  # 当前下载速度（从日志末尾抓）
  if ($LogFile -and (Test-Path $LogFile)) {
    $last = Get-Content $LogFile -Tail 30 | Select-String "\[download\]\s+[\d.]+%" | Select-Object -Last 1
    if ($last) { Write-Host "`n  当前: $($last.ToString().Trim())" -ForegroundColor Yellow }
  }
}

if ($Loop) {
  while ($true) {
    Show-Once
    # 全部完成则退出
    $allDone = $true
    foreach ($s in $Slug) {
      if (-not (Test-Path (Join-Path $Root "reference\$s\frames"))) { $allDone = $false }
    }
    if ($allDone) { Write-Host "`n全部完成 ✓" -ForegroundColor Green; break }
    Start-Sleep $Interval
  }
} else {
  Show-Once
}
