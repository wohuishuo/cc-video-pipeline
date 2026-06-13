---
name: ref-analyze
description: 参考视频解析（P0）。下载某 UP 主的视频，做秒级拆解——语音转文字、镜头切换点、响度节奏——并输出结构化分析报告（钩子位置、节奏、信息密度、可复用的结构 SOP）。当用户说"分析这个视频/参考一下这个 up 主/拆解这条视频的结构"时使用。
---

# 参考视频解析 (ref-analyze)

把一条优秀视频拆成可学习的结构，沉淀成 SOP。面向 Vlog 与科普两类（需要结构/节奏借鉴的）。

## 何时用
用户给一个视频链接（B站/抖音/YouTube/TikTok），想学它的开场钩子、节奏、信息密度、分段结构。

## 环境前提（已搭好）
- ffmpeg / yt-dlp 在 PATH（scoop）
- 转录双引擎：FunASR（中文高准确率+标点）+ faster-whisper（多语言/抗噪）
- 统一入口：`tools/transcribe_dispatch.py`（自动路由），走 venv（**勿用系统 Python 3.14**）
- 产物落在 `reference/<slug>/`

## 流程

### 1. 下载 + 抽音频
```powershell
.\.claude\skills\ref-analyze\scripts\fetch.ps1 -Url "<链接>" -Slug "<up主-选题名>"
```
产出：`reference/<slug>/` 下的 `video.mp4`、`audio.wav`、`*.info.json`、缩略图。

### 2. 语音转文字（智能路由）
```powershell
# 推荐：自动路由 — 中文走 FunASR（高准确率+标点），其他走 faster-whisper
.\tools\.venv\Scripts\python.exe .\tools\transcribe_dispatch.py ".\reference\<slug>\audio.wav" --lang auto

# 或手动指定引擎：
.\tools\.venv\Scripts\python.exe .\tools\transcribe.py         ".\reference\<slug>\audio.wav" --lang auto   # faster-whisper
.\tools\.venv\Scripts\python.exe .\tools\transcribe_funasr.py  ".\reference\<slug>\audio.wav" --lang zh     # FunASR
```
产出：`audio.srt`（字幕，FunASR 已带标点）、`audio.json`（段级时间戳）。
- 中文推荐 FunASR：WER ~3.2%（whisper ~8.7%），标点 91.3%，支持热词定制。
- 多语言/噪音场景用 faster-whisper（99 语言 + 抗噪更强）。
- 首次运行 FunASR 会自动下载模型 ~1GB。

### 3. 客观信号 + 抽帧
```powershell
.\.claude\skills\ref-analyze\scripts\probe.ps1 -Dir ".\reference\<slug>"
.\.claude\skills\ref-analyze\scripts\extract_frames.ps1 -Video ".\reference\<slug>\video.mp4" -OutDir ".\reference\<slug>\frames" -Cuts ".\reference\<slug>\cuts.txt" -MaxFrames 120
```
产出：`cuts.txt`（镜头切换）、`rms.txt`（响度包络）、`frames/`（关键帧图片，供 Claude 视觉分析）。

### 4. 生成分析报告（这一步由我 Claude 完成）
读取 `audio.json` + `cuts.txt` + `rms.txt` + `*.info.json` + `frames/*.jpg`，按下面模板写 `analysis.md`。
把转录文本按时间轴对齐镜头切换点和抽帧画面，标注：
- **0–8s 钩子**：开场怎么留人（提问/冲突/利益点/反常识）
- **结构骨架**：分了几段，每段功能（钩子→背景→展开→高潮→收尾→引导互动）
- **视觉手法**：镜头语言/字体/色板/转场方式/图形特效
- **节奏**：平均每个镜头时长、信息密度（每分钟新信息点）、语速
- **可复用 SOP**：抽象成"我下次能照搬的结构模板"

## 分析报告模板（写到 reference/<slug>/analysis.md）
```markdown
# 分析：<标题>
- 来源/UP主/时长/播放量（取自 info.json）

## 一句话结构
<金字塔顶：这条视频靠什么留住人>

## 秒级时间轴（含视觉）
| 时间 | 镜# | 帧图 | 画面内容 | 口播要点 | 镜头/动效 | 功能 |
|---|---|---|---|---|---|---|
| 0:00-0:06 | 1 | ![](frames/grid_00001.jpg) | ... | ... | 特写/推拉 | 钩子 |

## 节奏数据
- 总镜头数 / 平均镜头时长 / 语速(字/分) / 信息密度
- BGM 能量曲线 / 高潮点 / 留白段

## 钩子拆解
<前 8 秒逐句分析，含对应帧画面>

## 视觉手法总结
- 主色调 / 字体风格 / 转场方式 / 图形特效
- 竖屏适配建议（9:16 裁切/重构方案）

## 可复用 SOP
1. ...
2. ...

## 我能直接抄的点 / 我会改的点
```

## 注意
- B站/抖音可能需要 cookies（会员/分区）；失败时让用户导出 cookies，fetch.ps1 加 `--cookies-from-browser`。
- 出海视频（TikTok 外语）转录 `--lang auto` 即可，whisper 支持中俄英日。
- 抽帧上限 120 张（长视频自动拉大间隔），图片 720px 宽控制 token 消耗。
