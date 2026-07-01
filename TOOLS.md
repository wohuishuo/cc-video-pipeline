# 工具手册

**每当你不知道"这事该用哪个工具"时，先看这里。** 我会持续更新。

---

## 一、速查表：我要做什么 → 用什么

| 我要做什么 | 用哪个工具 | 一句话 |
|---|---|---|
| 下载一个 B站/YouTube 视频 | `fetch.ps1` | yt-dlp 包装，自动抽音频 |
| 把视频转成文字（中文） | `transcribe_dispatch.py --lang zh` | 自动走 FunASR，标点 91% |
| 把视频转成文字（外语） | `transcribe_dispatch.py --lang auto` | 自动走 faster-whisper |
| 检测视频的镜头切换点 | `probe.ps1` | 纯 ffmpeg，秒出 cuts.txt |
| 从视频里抽关键帧图片 | `extract_frames.ps1` | 两种模式：间隔+切镜点 |
| 分析一条参考视频的完整结构 | `p0_pipeline.ps1` | 一键跑上面所有步骤 |
| 拿 B站视频的播放量/评论数据 | `bilibili_data.py bv <BV号>` | 输出 JSON |
| 查 B站视频有没有 CC 字幕 | bilibili-mcp `get_video_info` | 不下载视频就能读字幕 |
| 切掉口播里的静音/气口 | `silence_cut.ps1` | 去停顿、去空白 |
| 把横屏视频转成竖屏 | `to_vertical.ps1` | 三种模式：模糊/裁切/字幕条 |
| 生成字幕文件（中文） | `transcribe_funasr.py --lang zh` | FunASR，比 whisper 准 |
| 生成字幕文件（外语） | `transcribe.py --lang auto` | faster-whisper，99 语言 |
| 让 CCD 重启后能用 B站工具 | 已配好，重启即可 | bilibili-mcp 已写入配置 |
| 检查环境是否正常 | `setup.ps1` | 自检 ffmpeg/venv/QSV 全绿 |
| 用代码生成视频动画 | Remotion (`tools/remotion-hello/`) | React 组件 → mp4 |
| 纳西妲/多语言本地配音 | `local-tts-dub` skill | 稳定 CPU 生产版 + Transformers 5/XPU 实验路由 |
| 查 Remotion 适合做什么 | `tools/remotion-eval.md` | 评估笔记 |
| 做小Lin风格知识/读书视频 | `docs/workflows/xiaolin-style-video.md` | 从选题→稿子→视觉支撑→剪辑的总 SOP |

---

## 二、转录引擎：我该用哪个？

**一句话决策：中文用 FunASR，其他用 faster-whisper，不确定用 dispatch。**

| 属性 | FunASR | faster-whisper |
|---|---|---|
| 中文准确率 | **WER 3.2%**（高） | WER 8.7%（较低） |
| 标点恢复 | **91.3%**（自带） | 68.5%（不准） |
| 多语言 | 中/英/日/韩/粤 | **99 种** |
| 抗噪音 | 较弱 | **较强** |
| 热词定制 | ✅ 支持 | ❌ 不支持 |
| 模型大小 | ~1GB | ~3GB (large-v3) |
| 首次下载 | 自动下载 Paraformer | 自动下载 large-v3 |

### 命令速查

```powershell
# 中文视频 → FunASR（推荐）
.\tools\.venv\Scripts\python.exe .\tools\transcribe_funasr.py ".\audio.wav" --lang zh

# 外语/多语言/噪音大 → faster-whisper
.\tools\.venv\Scripts\python.exe .\tools\transcribe.py ".\audio.wav" --lang auto

# 不知道什么语言 → 自动路由（推荐日常用）
.\tools\.venv\Scripts\python.exe .\tools\transcribe_dispatch.py ".\audio.wav" --lang auto
```

### 输出物（三种方式相同）
- `audio.srt` — 字幕文件，可烧录
- `audio.json` — 段级+词级时间戳，喂给分析脚本

---

## 三、B站工具矩阵：我该用哪个？

有三个途径可以获取 B站数据，各有用处。

| 工具 | 途径 | 要不要 cookie | 能做什么 |
|---|---|---|---|
| **bilibili-mcp** | CCD 内直接用 | 需要配（有引导） | 读 CC 字幕、拿元数据、看热门评论 |
| **fetch.ps1** | yt-dlp 下载 | 需要 cookies.txt | 下载高清视频+音频+缩略图+info.json |
| **bilibili_data.py** | Python 脚本 | cookies.txt 可选 | 查播放量/弹幕/评论/UP主/搜索 |

### 什么时候用哪个？

```
我想知道这个视频讲了什么（不下载）
  → bilibili-mcp get_video_info  （读 CC 字幕直接给摘要）

我想下载这个视频到本地分析
  → fetch.ps1  （yt-dlp，输出 video.mp4 + audio.wav）

我想查这个视频的播放量/点赞/弹幕数据
  → bilibili_data.py bv BVxxx

我想看这个视频的弹幕内容
  → bilibili_data.py danmaku BVxxx

我想看这个视频的评论
  → bilibili_data.py comments BVxxx

我想搜 B站上某个关键词的热门视频
  → bilibili_data.py search "关键词" --count 20

我想查某个 UP 主有多少粉丝和视频
  → bilibili_data.py up <UID>
```

### bilibili-mcp 细节

已配在 `claude_desktop_config.json`，**重启 CCD 后生效**。重启后在对话里直接说：

- "帮我看看这个 B站视频讲了什么" → 自动调 `get_video_info`
- "帮我查这个视频有多少播放" → 自动调 `get_video_metadata`
- "给我这个视频的字幕文本" → 自动调 `get_video_transcript`

> ⚠️ 首次使用时会引导配 B站 Cookie。**cookie 不在我这边，在你浏览器里。**
> 安装 "Get cookies.txt LOCALLY" 扩展导出，或直接在 bilibili-mcp 里跟引导走。

---

## 四、P0 一键全流程 vs 分步跑

### 一键跑（推荐新手）

```powershell
.\.claude\skills\ref-analyze\scripts\p0_pipeline.ps1 -Url "<视频链接>" -Slug "up主名-选题"
```

做的事：下载 → 转录 → 镜头检测 → 响度 → 抽帧 → 汇总产物清单。

产出一屏幕告诉你 `reference/up主名-选题/` 下面所有文件。

### 分步跑（适合调试或只做某一步）

```powershell
# 只下载（已有视频就跳过）
.\fetch.ps1 -Url "..." -Slug "test"

# 只转录
.\tools\.venv\Scripts\python.exe .\tools\transcribe_dispatch.py ".\reference\test\audio.wav" --lang auto

# 只做信号提取
.\probe.ps1 -Dir ".\reference\test"

# 只抽帧
.\extract_frames.ps1 -Video ".\reference\test\video.mp4" -OutDir ".\reference\test\frames"
```

`p0_pipeline.ps1` 也支持跳过某步：
```powershell
# 已经有了视频和转录，只跑探针+抽帧
.\p0_pipeline.ps1 -Url "..." -Slug "test" -SkipDownload -SkipTranscribe
```

---

## 五、剪辑工具

### silence_cut.ps1 — 去静音/去气口

**什么时候用**：口播视频里有很多长时间停顿、呼吸空白，想一键切干净。

```powershell
.\silence_cut.ps1 -Video ".\input.mp4" -Out ".\output.mp4"
.\silence_cut.ps1 -Video ".\input.mp4" -Out ".\output.mp4" -Noise "-30dB" -MinDuration 2.0
```

- `-Noise`：静音阈值，默认 -35dB（越小越敏感）
- `-MinDuration`：最少持续多少秒才算静音，默认 1.5s

**不做什么**：不识别口误/重复/纠正。那是 AI 语义审核的事，后续版本做。

### to_vertical.ps1 — 横屏转竖屏

**什么时候用**：做完横屏版本要发抖音/TikTok/视频号。

```powershell
.\to_vertical.ps1 -Video ".\input.mp4" -Out ".\output_9x16.mp4" -Mode blur     # 模糊背景（推荐）
.\to_vertical.ps1 -Video ".\input.mp4" -Out ".\output_crop.mp4" -Mode crop     # 居中裁切
.\to_vertical.ps1 -Video ".\input.mp4" -Out ".\output_cap.mp4" -Mode captions  # 上下留黑+字幕
```

三种模式对比：
| 模式 | 效果 | 适合场景 |
|---|---|---|
| blur | 原视频放大做模糊背景，主体居中 | 主体不在正中间的视频（推荐）|
| crop | 居中裁切 9:16 区域 | 主体始终在画面中央的视频 |
| captions | 上下黑条，视频缩到中间 | 需要保留全部画面的视频 |

---

## 六、数据工具

### bilibili_data.py

```powershell
.\tools\.venv\Scripts\python.exe .\tools\bilibili_data.py bv BV1xx          # 视频元数据
.\tools\.venv\Scripts\python.exe .\tools\bilibili_data.py danmaku BV1xx     # 弹幕列表
.\tools\.venv\Scripts\python.exe .\tools\bilibili_data.py comments BV1xx    # 热门评论
.\tools\.venv\Scripts\python.exe .\tools\bilibili_data.py up 12345          # UP主信息
.\tools\.venv\Scripts\python.exe .\tools\bilibili_data.py search "科普"     # 搜视频

# 输出到文件而非屏幕
.\tools\.venv\Scripts\python.exe .\tools\bilibili_data.py bv BV1xx --out data\video_BV1xx.json
```

返回的 JSON 字段：

**视频元数据**：`bvid`, `title`, `desc`, `duration`, `owner.name`, `stat.view`, `stat.like`, `stat.coin`, `stat.favorite`, `stat.share`, `stat.danmaku`, `stat.reply`, `tags`, `tname`(分区)

**弹幕**：`[{time, text, mode}, ...]`

**评论**：`[{user, content, like, replies}, ...]`

---

## 七、其他工具

### Remotion（代码生成动画）

位置：`tools/remotion-hello/`

```powershell
cd tools\remotion-hello
npm start            # 打开 Remotion Studio 预览
npm run build        # 渲染 out.mp4
```

**适合**：科普视频的图示/数据可视化/字幕特效
**不适合**：实拍视频剪辑（那是 ffmpeg 的活）
详见：`tools/remotion-eval.md`

### setup.ps1（环境自检）

```powershell
.\tools\setup.ps1
```

自检清单：ffmpeg、yt-dlp、node、faster-whisper、FunASR、Intel QSV

---

## 八、Skill 全家福

| Skill | 级别 | 状态 | 一句话 |
|---|---|---|---|
| `ref-analyze` | P0 | ✅ 完整可用 | 参考视频解析——下载→转录→镜头→抽帧→报告 |
| `content-plan` | P1 | 骨架 | 选题与标题生成 |
| `script-pyramid` | P1 | 骨架 | 金字塔原理写稿 |
| `storyboard` | P1 | 骨架 | 口播稿→分镜表 |
| `edit-ffmpeg` | P2 | ✅ 可用 | 静音切除 + 横竖屏转换 |
| `thumbnail` | P2 | 骨架 | 封面帧选取 + 版式方案 |
| `localize-video` | P2 | 🆕 骨架 | 视频本地化编排（转录→翻译→配音→烧字幕） |
| `review-data` | P3 | 骨架 | 数据复盘模板 |

> "骨架"表示 SKILL.md 写了流程和输出模板，但没有独立脚本。这些 skill 由我（Claude）按文档手工执行。

---

## 九、我到底该怎么开始？

### 场景 A：我要分析一条 B站 视频，学习它的结构

```
1. 重启 CCD（让 bilibili-mcp 生效）
2. 告诉 Claude："用 bilibili-mcp 帮我看看 BVxxx"
3. 拿到字幕摘要 → 觉得值得深入 → 跑 p0_pipeline.ps1
4. 告诉 Claude："读产物写 analysis.md"
```

### 场景 B：我要下载自己的口播素材，粗剪后发 B站+抖音

```
1. 把素材放到 projects/新视频/
2. 跑 silence_cut.ps1 去气口 → 得粗剪版
3. 粗剪版直接发 B站（横屏）
4. 跑 to_vertical.ps1 -Mode blur → 得竖屏版发抖音
```

### 场景 C：我要做科普视频，需要写稿+做动画

```
1. 告诉 Claude："用 script-pyramid 写一篇关于 XXX 的稿子"
2. Claude 输出 script.md
3. 告诉 Claude："用 storyboard 拆成拍镜脚本"
4. 用 Remotion 做动画图示 → 合成成片
5. 跑 to_vertical.ps1 出竖屏版
```
