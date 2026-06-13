---
name: edit-ffmpeg
description: 剪辑自动化（P2）。ffmpeg 脚本做粗剪、卡点、字幕烧录、横竖屏双版本导出，走 Intel Arc QSV 硬件编码。跳舞视频的音乐卡点也在这里。当用户说"粗剪/烧字幕/导竖屏版/卡点"时使用。
---

# 剪辑自动化 (edit-ffmpeg) — 可用版

## 硬件
Intel Arc QSV：编码用 `-c:v h264_qsv` 或 `hevc_qsv`，比 CPU 软编快很多。先跑 `tools/setup.ps1` 确认 QSV 可用。

## 已实现的能力

### 1. 静音切除（口播粗剪第一步）
```powershell
.\.claude\skills\edit-ffmpeg\scripts\silence_cut.ps1 -Video ".\input.mp4" -Out ".\output.mp4"
# 可选参数
.\.claude\skills\edit-ffmpeg\scripts\silence_cut.ps1 -Video ".\input.mp4" -Out ".\output.mp4" -Noise "-30dB" -MinDuration 1.5
```
- 自动检测静音段（默认 -35dB / 持续 >1.5s）
- 切除后拼接有效段，c:v copy 不重编码（快速）
- 注：这是无语义的纯信号静音检测；AI 语义审核（口误/重复/纠正）待后续版本

### 2. 横竖屏转换
```powershell
# 模糊填充背景（推荐，视觉舒适）
.\.claude\skills\edit-ffmpeg\scripts\to_vertical.ps1 -Video ".\input.mp4" -Out ".\output_9x16.mp4" -Mode blur

# 主体居中裁切（适合主体始终在中间的）
.\.claude\skills\edit-ffmpeg\scripts\to_vertical.ps1 -Video ".\input.mp4" -Out ".\output_crop.mp4" -Mode crop

# 上下留黑 + 字幕烧录
.\.claude\skills\edit-ffmpeg\scripts\to_vertical.ps1 -Video ".\input.mp4" -Out ".\output_cap.mp4" -Mode captions -Subtitle ".\audio.srt"
```
- 横屏 16:9 → 竖屏 1080x1920
- 默认 Intel QSV 硬编，失败自动退到 CPU 软编

### 3. 人脸追踪横转竖（多人对谈/采访/播客）
```powershell
.\.claude\skills\edit-ffmpeg\scripts\reframe.ps1 -Video ".\podcast.mp4"
.\.claude\skills\edit-ffmpeg\scripts\reframe.ps1 -Video ".\interview.mp4" -Motion smooth -FacePick speaker
```
- 移植自 jianshuo/wjs-reframing-video，裁切窗口**跟随正在说话的人**（嘴部开合方差判定）
- 依赖 venv 的 mediapipe+opencv；首次运行下载 ~4MB 模型
- 产出 `*_cropped.mp4` + `*.crop.json`（裁切方案存档），原视频不动
- **单人/无脸内容用 `to_vertical.ps1` 即可**，不必动用人脸追踪
- 看日志 `face#N: Xs on screen`，若全是 `(no face/fallback)` 说明没检测到脸 → 改用 to_vertical

### 4. 字幕烧录
```powershell
ffmpeg -i input.mp4 -vf "subtitles=audio.srt:force_style='FontSize=18,Alignment=2'" -c:v h264_qsv output_subbed.mp4
```
- SRT 文件来自 transcribe.py / transcribe_funasr.py / transcribe_dispatch.py
- FunASR 转录的 SRT 已带标点，可直接烧录

### 4. 双版本批量导出
```powershell
# 一次产出 B站横屏(16:9) + 抖音/TikTok竖屏(9:16)
ffmpeg -i input.mp4 -c:v h264_qsv -preset medium out_horiz.mp4
.\.claude\skills\edit-ffmpeg\scripts\to_vertical.ps1 -Video input.mp4 -Out out_vert.mp4 -Mode blur
```

## 计划做的能力
- [ ] **卡点**（跳舞视频）：节拍检测（librosa / aubio），按 beat 切镜。下次做 `beat_detect.py`
- [ ] **AI 语义审核**：配合 FunASR 转录结果，自动识别口误/重复/纠正/卡顿，生成审核网页，人工确认后自动剪辑（借鉴 videocut-skills 思路）
- [ ] **调色**：LUT 应用、对比度/饱和度批量调整
- [ ] **自动粗剪→手工精修管线**：粗剪导出格式兼容必剪导入，保留人工精修环节

## TODO
- [ ] beat_detect.py（librosa 节拍检测 → 切镜时间点）
- [ ] review_cut.ps1（AI 语义审核 → 确认网页 → ffmpeg 剪辑）
- [ ] color_grade.ps1（批量调色）
