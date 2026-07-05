<#
.SYNOPSIS
  切除视频中的静音段（ffmpeg silencedetect）。
  口播粗剪的第一步：去气口/去过长停顿。
  默认用 filter_complex 精确到帧切割（re-encode），失败时回退 concat demuxer。
.EXAMPLE
  .\silence_cut.ps1 -Video "C:\...\input.mp4" -Out "C:\...\output.mp4"
.EXAMPLE
  .\silence_cut.ps1 -Video "C:\...\input.mp4" -Out "C:\...\output.mp4" -Noise -30dB -MinDuration 1.5
#>
param(
  [Parameter(Mandatory = $true)][string]$Video,
  [Parameter(Mandatory = $true)][string]$Out,
  [string]$Noise = "-35dB",
  [double]$MinDuration = 1.5
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $Video)) { throw "Video not found: $Video" }

Write-Host "[*] 检测静音（阈值 $Noise，至少持续 ${MinDuration}s）…"

# ── Step 1: silencedetect ──
$detect_raw = & ffmpeg -i $Video -af "silencedetect=noise=$Noise:d=$MinDuration" -f null - 2>&1

$silence_starts = @()
$silence_ends   = @()
foreach ($line in $detect_raw) {
  if ($line -match "silence_start: ([\d.]+)") { $silence_starts += [double]$Matches[1] }
  if ($line -match "silence_end: ([\d.]+)")   { $silence_ends   += [double]$Matches[1] }
}
Write-Host "[*] 检测到 $($silence_starts.Count) 个静音段"

# 去重交叉
$silences = [System.Collections.Generic.List[object]]::new()
for ($i = 0; $i -lt $silence_starts.Count; $i++) {
  $s = $silence_starts[$i]
  $e = if ($i -lt $silence_ends.Count) { $silence_ends[$i] } else { $s + $MinDuration }
  if ($i -gt 0 -and $s -lt $silences[-1].End) { continue }
  $null = $silences.Add(@{ Start = $s; End = $e })
}

# ── Step 2: 反选，取有效段 ──
$keep_segments = [System.Collections.Generic.List[object]]::new()
$last_end = 0.0
foreach ($sil in $silences) {
  if ($sil.Start - $last_end -gt 0.01) {
    $null = $keep_segments.Add(@{ Start = $last_end; End = $sil.Start })
  }
  $last_end = $sil.End
}
$dur_raw = & ffmpeg -i $Video 2>&1 | Select-String "Duration: ([0-9:.]+)"
if ($dur_raw -match "Duration: (\d+):(\d+):(\d+\.?\d*)") {
  $total_dur = [double]$Matches[1] * 3600 + [double]$Matches[2] * 60 + [double]$Matches[3]
  if ($total_dur - $last_end -gt 0.01) {
    $null = $keep_segments.Add(@{ Start = $last_end; End = $total_dur })
  }
}

if ($keep_segments.Count -eq 0) {
  Write-Host "[warn] 没有找到非静音段，输出原视频"
  Copy-Item $Video $Out -Force
  exit 0
}
Write-Host "[*] 保留 $($keep_segments.Count) 个有效段"

# ── Step 3: filter_complex 精确切割（frame-accurate）──
# 修复 1：每个 trim 段用唯一标签 [v0o][v1o]...[vNo] 避免 concat 找不到输入流
# 修复 2：re-encode 而非 -c copy，保证非 keyframe 位置也能精确切割
Write-Host "[*] 精确切割（filter_complex, frame-accurate）…"
$vparts = [System.Collections.Generic.List[string]]::new()
$aparts = [System.Collections.Generic.List[string]]::new()
for ($i = 0; $i -lt $keep_segments.Count; $i++) {
  $seg = $keep_segments[$i]
  $dur = $seg.End - $seg.Start
  $vparts.Add("[0:v]trim=start=$($seg.Start):duration=$dur,setpts=PTS-STARTPTS[v$($i)o]")
  $aparts.Add("[0:a]atrim=start=$($seg.Start):duration=$dur,asetpts=PTS-STARTPTS[a$($i)o]")
}

$vlabels = ($(0..($vparts.Count-1) | % { "[v${_}o]" }) -join "")
$alabels = ($(0..($aparts.Count-1) | % { "[a${_}o]" }) -join "")
$vgraph = ($vparts -join "; ") + "; " + $vlabels + "concat=n=$($vparts.Count):v=1:a=0[v]"
$agraph = ($aparts -join "; ") + "; " + $alabels + "concat=n=$($aparts.Count):v=0:a=1[a]"

ffmpeg -y -i $Video -filter_complex "$vgraph; $agraph" -map "[v]" -map "[a]" `
  -c:v libx264 -crf 18 -preset fast -c:a aac -b:a 192k $Out 2>$null

if ($LASTEXITCODE -eq 0) {
  Write-Host "[ok] 粗剪完成（精确到帧）-> $Out"
  exit 0
}

# ── 兜底：concat demuxer（keyframe 精度）──
# 修复 3：Set-Content（非 Out-File -Append）避免 UTF-8 BOM 导致 ffmpeg concat 解析失败
Write-Host "[warn] filter_complex 失败，回退 concat demuxer（keyframe 精度）…" -ForegroundColor Yellow
$concat_file = "$env:TEMP\silence_concat_$(Get-Random).txt"
$idx = 0
foreach ($seg in $keep_segments) {
  $tmp_out = "$env:TEMP\silence_part_${idx}.mp4"
  ffmpeg -y -ss $seg.Start -t ($seg.End - $seg.Start) -i $Video -c copy -avoid_negative_ts make_zero $tmp_out 2>$null
  if ($LASTEXITCODE -eq 0) {
    if ($idx -eq 0) {
      "file '$tmp_out'" | Set-Content -Encoding ascii $concat_file
    } else {
      "file '$tmp_out'" | Add-Content -Encoding ascii $concat_file
    }
  }
  $idx++
}

if ((Get-Content $concat_file -ErrorAction SilentlyContinue | Measure-Object -Line).Lines -gt 0) {
  ffmpeg -y -f concat -safe 0 -i $concat_file -c copy $Out 2>$null
  if ($LASTEXITCODE -eq 0) {
    Write-Host "[ok] 粗剪完成（keyframe 精度）-> $Out" -ForegroundColor Yellow
  } else {
    Write-Host "[warn] concat 失败，输出原视频" -ForegroundColor Red
    Copy-Item $Video $Out -Force
  }
} else {
  Write-Host "[warn] concat 列表为空，输出原视频" -ForegroundColor Red
  Copy-Item $Video $Out -Force
}

# 清理临时文件
Remove-Item $concat_file -Force -ErrorAction SilentlyContinue
Get-ChildItem "$env:TEMP\silence_part_*.mp4" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
