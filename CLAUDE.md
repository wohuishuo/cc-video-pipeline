# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目性质

这不是传统代码仓库——这是**基于 Claude Code skills 的视频创作流水线**，脚本+SKILL.md 驱动。用户（卡夏-Kasya）做三类视频：Cos跳舞（主）、Vlog、科普。

## 启动前必读

先看 [TOOLS.md](TOOLS.md) 了解所有工具的使用方式。

**接手新机器/重装时**：先看 [INSTALL_HISTORY.md](INSTALL_HISTORY.md) 知道已装什么，**别重复装**。

**每次开始工作时**：跑 `.\tools\setup.ps1` 做环境自检（ffmpeg/venv/QSV 全绿才算正常）

## 环境硬约束——必须遵守

- **OS**: Windows 11 原生 PowerShell（非 WSL）
- **Python**: 所有 AI 库走 `tools\.venv`（Python 3.12），系统 Python 是 3.14 **不能用**
- **npm**: 所有 npx 命令设 `$env:npm_config_cache = "C:\Users\艾莉\.npm-cache"`（中文用户名乱码）
- **GPU**: Intel Arc 140T 核显（无 NVIDIA），剪辑走 QSV `h264_qsv`/`hevc_qsv`
- **路径**: 所有路径含中文"艾莉""视频剪辑"，ffmpeg/cv2 用绝对路径，subprocess 设 `encoding="utf-8", errors="replace"`

## 关键已知坑——不要重复踩

参见 BUGFIXES.md 中已修复的 6 个 bug：
1. ffmpeg filter_complex concat 标签必须唯一（不可全 [v]）
2. Windows 路径 `C:\...` 的冒号在 ffmpeg filtergraph 中被误解析 → 用 `filename='...'` 格式
3. bilibili_api 的 `page_index` 是 0-based
4. `--js-runtimes` 必须单独一个参数组
5. 静音切除参考 jianshuo 的 `--reencode` 方式（frame-accurate），`-c copy` 走 keyframe 不准
6. probe.ps1 检测到的切镜时间是"切换后的帧"→ 需 -0.04s 修正

另：B站下载限速不能开 aria2c（会静默截断音频），用 yt-dlp 原生下载+`--format-sort +vcodec:avc`；yt-dlp `--cookies-from-browser edge` 不可用（Edge锁cookie db），必须手动导出 cookies.txt

## 脚本分层——什么时候直接用，什么时候用 Python venv

| 层 | 技术 | 入口 |
|---|---|---|
| 视频下载/分析/剪辑 | PowerShell + ffmpeg + yt-dlp | `.ps1` 脚本直接跑 |
| AI（转录/NLP） | Python 3.12 venv | `.\tools\.venv\Scripts\python.exe .\tools\xxx.py` |
| 动画生成 | Node + React | `cd tools\remotion-hello; npm run ...` |

## 常见操作速查

| 操作 | 命令 |
|---|---|
| 环境自检 | `.\tools\setup.ps1` |
| 分析参考视频（一键） | `.\.claude\skills\ref-analyze\scripts\p0_pipeline.ps1 -Url "..." -Slug "up-选题"` |
| 下载 B站视频 | `.\.claude\skills\ref-analyze\scripts\fetch.ps1 -Url "..." -Slug "..."` |
| 静音切除 | `.\.claude\skills\edit-ffmpeg\scripts\silence_cut.ps1 -Video "in.mp4" -Out "out.mp4"` |
| 横屏转竖屏 | `.\.claude\skills\edit-ffmpeg\scripts\to_vertical.ps1 -Video "in.mp4" -Out "out.mp4" -Mode blur` |
| 语音转文字 | `.\tools\.venv\Scripts\python.exe .\tools\transcribe_dispatch.py "audio.wav" --lang auto` |

## Skill 的两种形态

**有脚本的**（自动化运行）: ref-analyze, edit-ffmpeg
**骨架的**（Claude 读 SKILL.md 手工执行）: content-plan, script-pyramid, storyboard, thumbnail, localize-video, review-data

"骨架"并非不能用——这些是内容创作 skill，由 Claude 按 SKILL.md 中的模板和规范直接输出结果。P1 skill 等本身是"AI 写东西"，不需要外部脚本。

**脚本位置**：所有 `.ps1` 脚本在 `.claude/skills/<skill>/scripts/` 下。`.agents/skills/` 是旧备份，勿直接使用。

## reference/ 目录的生命周期

```
reference/<slug>/
  video.mp4                ← .claude/skills/ref-analyze/scripts/fetch.ps1 下载
  audio.wav                ← fetch.ps1 自动提
  audio.json / audio.srt   ← tools/transcribe_dispatch.py 产出
  cuts.txt / rms.txt       ← .claude/skills/ref-analyze/scripts/probe.ps1 产出
  frames/*.jpg             ← .claude/skills/ref-analyze/scripts/extract_frames.ps1 产出
  analysis.md              ← Claude 读上面文件后手写
```

## MCP 工具——对话内可直接调

用户重启 CCD 后，在对话中你说"帮我看看 BVxxx"或"这个视频讲什么"即可调用：
- `bilibili-mcp`: get_video_info, get_video_transcript, get_video_comments, get_video_metadata
- `playwright`: 直接控制 Edge（含登录态），导航、点击、截图

## 三类视频的生产流水线

| 类型 | P0 参考分析 | P1 内容生产 | P2 剪辑 | 特殊需求 |
|---|---|---|---|---|
| Cos跳舞 | 分析同赛道 UP 主 | 标题+封面方案 | 卡点+调色+竖屏 | 跳拍音乐 beat 检测 |
| 科普 | 分析口播/书单类结构 | 金字塔稿+分镜+Remotion动画 | 烧字幕+双版本导出 | 图示/数据可视化 |
| Vlog | 分析生活/读后感类 | 选题+稿 | 去气口+字幕+竖屏 | 日常感保留 |

## 用户偏好

- 程序员，要流程自动化、开源优先、本地优先——一条命令解决
- 写稿**强制金字塔结构**（结论先行），是个人表达训练重点
- 优势语言: 中/俄/英/日——TikTok 出海是差异化方向
- 外部参考已学习: jianshuo/claude-skills, videocut-skills, garden-skills

## 当你需要分析视频时

已有的两个 analysis.md 作为参考模板:
- `reference\商业金融书单\analysis.md` — 小Lin 10分钟书单 SOP（每本书固定模板：书名+私人故事+具体例子+作者+推荐）
- `reference\曙光-分享喜讯\analysis.md` — 一五老师 3分钟口播 SOP（热点→政策背书→理念输出→号召互动）

无论分析什么视频，都要产出:
1. 全程秒级时间轴（含画面内容+口播要点+镜头/动效手法）
2. 可复用的结构模板（照抄即可的填空式 SOP）
3. 对用户（艾莉）的针对性建议（她的类目×这条视频的手法）
