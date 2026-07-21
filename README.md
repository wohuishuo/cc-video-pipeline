# cc 视频创作流水线

## New MVP architecture

The first clean vertical slice is the research domain core. Run its substitute-adapter demonstration with:

```powershell
.\tools\.venv\Scripts\python.exe -m research_mvp `
  --workspace "$env:TEMP\research-mvp-demo" `
  create demo:video-1
```

`research-mvp` is domain-verified with substitute adapters. Real Bilibili/YouTube, FFmpeg, and transcription adapters remain platform-integration work. See `docs/mvp/research/` for the brief, DAG, evidence, and delivery ledger.

> **结论先行** —— 这是一套基于 Claude Code skills 的视频创作工具链。
> 把"参考视频分析 → 内容策划 → 写稿 → 剪辑辅助 → 封面标题 → 数据复盘 → 本地化出海"七步流水线，全部跑在 Windows 本地，开源、零云端依赖。

---

## 1. 项目本质

这不是传统代码仓库——它**没有主程序**，而是一组**可独立运行的小工具**，围绕"做视频"这个目标互相配合。

你用 Claude Code 当"大脑"，调用这些工具当"手脚"，组合出你需要的视频工作流。

**目标用户**：做 Vlog / 科普 / Cos 跳舞类视频的创作者；会 PowerShell + Python 基础；不信任云端 API；想一个命令搞定全流程。

**项目体量**：约 20 个 .ps1 脚本 + 10 个 Python 工具 + 8 个 Claude Code skill 的 SKILL.md 描述。

---

## 2. 一句话价值主张

> **你只需要想"我要做什么"——下载、转录、剪辑、做竖屏、查数据——剩下的命令我都帮你串好。**
> 没有 GUI，没有选项海洋，零学习成本。

---

## 3. 三大使用场景（按使用频率排序）

### 场景 A：分析别人的视频，学它的结构

```powershell
.\.claude\skills\ref-analyze\scripts\p0_pipeline.ps1 `
  -Url "https://www.bilibili.com/video/BVxxx" `
  -Slug "某up主-选题名"
# 产物在 reference/某up主-选题名/ 下，让 Claude 读 → 写 analysis.md
```

→ **30 秒启动，10 分钟拿到一份带镜头切换点、转录、抽帧、节奏数据的精读报告**。

### 场景 B：粗剪自己的口播素材

```powershell
.\.claude\skills\edit-ffmpeg\scripts\silence_cut.ps1 -Video .\raw.mp4 -Out .\cut.mp4
.\.claude\skills\edit-ffmpeg\scripts\to_vertical.ps1 -Video .\cut.mp4 -Out .\cut_9x16.mp4 -Mode blur
```

→ **两行命令，横屏版+竖屏版同时到手**。

### 场景 C：拉一个 UP 主的全部视频建知识库

```powershell
.\tools\.venv\Scripts\python.exe .\tools\search_up_videos.py 520819684 "小Lin说" "data/小Lin说/videos.json"
.\tools\.venv\Scripts\python.exe .\tools\render_xiaolin_table.py
```

→ **B 站 138 条视频全表 + 自动分类 + 候选参考 Top 15**。以后要做类似选题直接查表。

---

## 4. 工具地图（一张表查清楚）

| 我要做 | 用什么 | 复杂度 |
|---|---|---|
| 下载视频 | `fetch.ps1` | 1 行 |
| 语音转文字（中文） | `transcribe_dispatch.py` | 自动走 FunASR，WER 3.2% |
| 语音转文字（外语） | `transcribe_dispatch.py` | 自动走 faster-whisper，99 种语言 |
| 检测镜头切换 | `probe.ps1` | 纯 ffmpeg |
| 抽关键帧 | `extract_frames.ps1` | 间隔+切镜点两种模式 |
| 拉 B 站元数据 | `bilibili_data.py bv BVxxx` | 单条数据 |
| 拉 B 站全部视频 | `search_up_videos.py` | 翻页全表 |
| 渲染视频表 | `render_xiaolin_table.py` | markdown 表格+分类 |
| 去静音/气口 | `silence_cut.ps1` | filter_complex 帧精度 |
| 横转竖 | `to_vertical.ps1` | blur/crop/captions 三种 |
| 制作科普动画 | `tools/remotion-hello/` | React→mp4 |
| 环境自检 | `tools/setup.ps1` | 看全绿否 |
| B 站弹幕/评论 | `bilibili-mcp`（CCD 内） | 重启 CCD 后生效 |

完整版：见 [TOOLS.md](TOOLS.md)

---

## 5. 七大功能模块（P0 → P3 优先级）

### ✅ P0 — 参考视频解析（已完整可跑）

输入：B 站/YouTube 链接。输出：转录 + 镜头切换 + 抽帧 + 分析报告。

```
.claude/skills/ref-analyze/
├── SKILL.md              # skill 描述（什么时候触发）
└── scripts/
    ├── fetch.ps1         # 下载+抽音频
    ├── probe.ps1         # 镜头切换+响度
    ├── extract_frames.ps1 # 抽帧
    └── p0_pipeline.ps1   # 一键串联
```

### ✅ P2 — 剪辑自动化（已可用）

```
.claude/skills/edit-ffmpeg/scripts/
├── silence_cut.ps1   # 静音切除（filter_complex 帧精度，含 concat demuxer 兜底）
├── to_vertical.ps1   # 横转竖（3 种模式，QSV 加速）
└── reframe.ps1       # 人脸追踪横转竖（多机位/采访场景）
```

### 🆕 P2 — 视频本地化编排器（骨架）

`localize-video` skill：转录→翻译→配音→烧字幕→竖屏，用于把视频多语言出海（中→俄/英/日）。

### 📝 P1 — 内容生产（骨架，由 Claude 读 SKILL.md 手工执行）

| Skill | 用途 |
|---|---|
| `content-plan` | 选题 + 多版标题对比打分 |
| `script-pyramid` | 金字塔原理写稿（结论先行）|
| `storyboard` | 口播稿→分镜表 |

> P1 不需要脚本——这是"AI 写东西"的活，Claude 按 SKILL.md 模板直接出结果。

### 📊 P3 — 数据复盘（骨架）

`review-data` skill：跟踪每条视频的播放/完播/互动，反向优化选题。

### 🎨 P2 — 封面流程（骨架）

`thumbnail` skill：从视频抽帧选封面候选 + 版式方案。

### 🎬 Bonus — Remotion 动画

`tools/remotion-hello/` —— React 组件编程生成视频，**适合科普图示/数据可视化**，不适合实拍剪辑。详见 [remotion-eval.md](tools/remotion-eval.md)。

---

## 6. 环境约束（必读）

> 这套流水线假设你的机器是这套配置。如果不是，按下面 5 分钟装一下。

| 组件 | 要求 | 装法 |
|---|---|---|
| **OS** | Windows 11 + PowerShell 5.1+ | 自带 |
| **Python** | 3.12+（**绝不能用 3.14**）| `scoop install python@3.12` |
| **AI 库** | 装在 `tools/.venv/` | 见下方"安装" |
| **ffmpeg** | 8.1+ 含 QSV | `scoop install ffmpeg` |
| **yt-dlp** | 2025+ | `scoop install yt-dlp` |
| **Node** | v18+ | `scoop install nodejs` |
| **Intel QSV** | 核显（如 Intel Arc）| 自动检测，编辑用 `h264_qsv` 加速 |

**npm 缓存坑**：Windows 中文用户名（"艾莉"）下，npm 默认缓存会创建失败。**所有 npx 命令前设：**
```powershell
$env:npm_config_cache = "C:\Users\艾莉\.npm-cache"
```

---

## 7. 安装（5 分钟）

### Step 1：克隆 + 准备

```powershell
git clone https://github.com/你的用户名/cc视频剪辑.git
cd cc视频剪辑
```

### Step 2：建虚拟环境 + 装 AI 库

```powershell
python3.12 -m venv tools\.venv
.\tools\.venv\Scripts\python.exe -m pip install --upgrade pip
.\tools\.venv\Scripts\python.exe -m pip install `
  faster-whisper `
  funasr torch torchaudio `
  bilibili-api-python `
  edge-tts `
  mediapipe opencv-python
```

**首次跑会下载模型**（FunASR 1GB、faster-whisper large-v3 3GB），后续秒开。

### Step 3：跑自检确认环境

```powershell
.\tools\setup.ps1
```

应当看到全绿：
```
[OK] ffmpeg       C:\...\ffmpeg.exe
[OK] yt-dlp       C:\...\yt-dlp.exe
[OK] node         C:\...\node.exe
[OK] faster-whisper 1.2.1
[OK] FunASR      1.3.9
[OK] Intel QSV 硬件编码可用
```

### Step 4（可选）：配 B 站 Cookie

B 站对未登录用户限速。装个浏览器扩展就能让脚本用你的身份：

1. Edge 装 "Get cookies.txt LOCALLY"
2. 打开 bilibili.com 登录
3. 扩展 → Export As → 保存到 `reference/cookies.txt`

之后所有 `fetch.ps1` 都会自动用它。

---

## 8. 实战教程：从零分析一条 B 站视频

**目标**：把"小 Lin 说"的某条 10 分钟科普视频拆成可复用的 SOP。

```powershell
# 1. 一键分析
.\.claude\skills\ref-analyze\scripts\p0_pipeline.ps1 `
  -Url "https://www.bilibili.com/video/BV1xxxx" `
  -Slug "小Lin-日本财团"

# 2. 等下载+转录完成（约 2-10 分钟），看到这样的输出：
#    [ok] video + audio.wav 就绪
#    [ok] 检测到 87 个镜头切换
#    [ok] 抽帧 60 张

# 3. 产物清单
Get-ChildItem .\reference\小Lin-日本财团\
#    video.mp4  audio.wav  audio.json  audio.srt
#    cuts.txt   rms.txt     frames/    video.info.json

# 4. 让 Claude 读产物写 analysis.md
#    在 Claude Code 对话里说：
#    "读 reference/小Lin-日本财团/ 下的产物，写 analysis.md"
#    → 5 分钟出报告：钩子拆解、秒级时间轴、可复用 SOP
```

---

## 9. 项目目录（按上传 git 后的样子）

```
cc视频剪辑/
├── README.md                  # 你正在看
├── CLAUDE.md                  # 给 Claude Code 的项目笔记（自动记忆）
├── TOOLS.md                   # 完整工具手册（一页速查）
├── BUGFIXES.md                # 历史 bug 修复记录
├── .gitignore                 # 视频/帧/venv 全部不进 git
│
├── tools/                     # 通用工具（Python 脚本）
│   ├── .venv/                 # 虚拟环境（git 忽略）
│   ├── setup.ps1              # 环境自检
│   ├── transcribe.py          # faster-whisper
│   ├── transcribe_funasr.py   # FunASR 中文
│   ├── transcribe_dispatch.py # 统一入口
│   ├── bilibili_data.py       # 单条 B 站数据
│   ├── pull_channel_data.py   # 拉取 UP 主全部视频
│   ├── search_up_videos.py    # 备选拉取方案（搜索 API）
│   ├── render_xiaolin_table.py # 视频表渲染+分类
│   ├── remotion-hello/        # React→视频（git 忽略 node_modules）
│   └── remotion-eval.md       # Remotion 评估
│
├── .claude/skills/            # 8 个 Claude Code skill
│   ├── ref-analyze/           # ✅ P0 参考视频解析
│   ├── edit-ffmpeg/           # ✅ P2 剪辑自动化
│   ├── localize-video/        # 🆕 P2 本地化编排器
│   ├── content-plan/          # 📝 P1 选题（骨架）
│   ├── script-pyramid/        # 📝 P1 写稿（骨架）
│   ├── storyboard/            # 📝 P1 分镜（骨架）
│   ├── thumbnail/             # 📝 P2 封面（骨架）
│   └── review-data/           # 📝 P3 数据复盘（骨架）
│
├── projects/                  # 你自己做的视频项目（git 跟踪 templates，ignore 视频产物）
│   └── _template/             # 起步模板
│
├── reference/                 # 拉来的参考视频（**git 忽略**，大且含元数据）
│   ├── cookies.txt            #   ↑↑↑ 这个**绝对不要传** ↑↑↑
│   └── 小Lin-日本财团/        # 全部产物在 .gitignore 里
│
├── _refs/                     # 外部学习参考（git 忽略，独立 clone）
│   └── jianshuo-claude-skills/  # 我们学的对象
│
└── data/                      # 复盘数据 + 知识库
    ├── 我/                    # 你的 B 站账号数据
    └── 小Lin说/               # 拉来的 UP 主数据
        ├── videos.json        # 结构化数据
        └── videos_table.md    # 渲染的 markdown 表
```

---

## 10. 为什么这个项目值钱（5 个杀手特性）

| 特性 | 价值 |
|---|---|
| **完全本地** | 无云端、无 key、无月费 |
| **真·金字塔写稿** | 写稿强制结论先行，是个人表达训练 |
| **多语言出海** | 中→俄/英/日配音字幕全链路 |
| **可学习可改造** | 每个 skill 独立，能挑能改 |
| **一站式** | 从"看别人的视频"到"发自己视频"一气呵成 |

---

## 11. 外部参考（已学习借鉴）

| 项目 | 学了什么 |
|---|---|
| [jianshuo/claude-skills](https://github.com/jianshuo/claude-skills) | 15 个视频 skill 的"做一件事"命名哲学 |
| [Ceeon/videocut-skills](https://github.com/Ceeon/videocut-skills) | AI 语义审核→人工确认→自动剪辑闭环 |
| [ConardLi/garden-skills](https://github.com/ConardLi/garden-skills) | 文案→视频、稿子→演示画面 |
| [xzxzzx/bilibili-mcp](https://www.npmjs.com/package/@xzxzzx/bilibili-mcp) | B 站数据在 CCD 内直接调 |
| [FunASR](https://github.com/modelscope/FunASR) | 中文转录的事实标准 |
| [SocialSisterYi/bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect) | 18k stars 的 B 站野生 API 字典 |

---

## 12. Roadmap（按优先级）

- [ ] **内容生产 skill 自动化** — 给 `content-plan` / `script-pyramid` / `storyboard` 加 lint 脚本，AI 写完自动检查
- [ ] **AI 语义审核** — 配合 FunASR 转录，自动识别口误/重复/纠正，生成审核网页
- [ ] **字幕烧录工具** — `burn_sub.ps1`（libass 烧字幕到竖屏，借鉴 wjs-burning-subtitles）
- [ ] **B 站发布集成** — `upload_bili.ps1`（API 上传，自动配封面/标签/合集）
- [ ] **数据复盘自动化** — 每天拉取前 N 条视频数据，生成每周/月报表

---

## 13. 贡献

PR 欢迎。每个 skill 一个目录，独立版本号。SKILL.md 改描述、scripts/ 改实现都可以。

新加 skill 的格式：
- 目录名用 V-ing 动名词（参考 `wjs-transcribing-audio` 模式）
- 包含 `SKILL.md`（frontmatter 含 name/description/触发词）
- 脚本放同目录 `scripts/`

---

## 14. License

MIT。

---

> 最后更新：2026-06-13
> 项目根目录：[C:\Users\艾莉\Videos\cc视频剪辑](.)（路径因人而异，看你自己的）
