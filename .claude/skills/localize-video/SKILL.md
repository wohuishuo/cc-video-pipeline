---
name: localize-video
description: 视频本地化编排器（P2，部分实现）。把一条视频本地化为目标语言：转录→翻译→（配音）→烧字幕→竖屏导出。当用户说"帮我把这个视频做成中文字幕/翻译成英文/配俄语音/全套本地化"时使用。注意：翻译/配音步骤尚未自动化，由 Claude 手工完成或待补脚本。
---

# 视频本地化 (localize-video) — 编排器（⚠️ 部分实现）

> 这是个**编排器**：本身不做活，只把任务路由到各步骤。
> 设计参考 `_refs/jianshuo-claude-skills/wjs-localizing-video`（mac/bash 版，可照着补脚本）。

## 当前每步真实状态

| 步骤 | 工具 | 状态 |
|---|---|---|
| 1. 转录 | `tools/transcribe_dispatch.py`（ref-analyze）| ✅ 可跑 |
| 2. 翻译 | **由我 Claude 直接翻译 SRT** | ⚠️ 无脚本，手工。规则见下 |
| 3. 配音 | `scripts/tts_dub.py`（Edge TTS，中俄英日）| ✅ 可跑 |
| 4. 烧字幕 | `edit-ffmpeg/to_vertical.ps1 -Mode captions` | ✅ 可跑 |
| 5. 竖屏 | `edit-ffmpeg/to_vertical.ps1` 或 `reframe.ps1` | ✅ 可跑 |

**全链路现已打通**：转录 → 我翻译 → 配音 → 烧字幕 → 竖屏导出（中俄英日完整出海版）。

## 配音 tts_dub.py
```powershell
# SRT → 时间对齐配音，mux 回视频。免费 Edge TTS，无需 key。
.\tools\.venv\Scripts\python.exe .\.claude\skills\localize-video\scripts\tts_dub.py `
  --video "$d\video.mp4" --srt "$d\audio.ja.srt" --lang ja
# 男声 / 调速 / 指定音色：
.\tools\.venv\Scripts\python.exe .\.claude\skills\localize-video\scripts\tts_dub.py `
  --video "$d\video.mp4" --srt "$d\audio.ru.srt" --lang ru --gender male --rate "-5%"
```
- 支持 `--lang zh|en|ru|ja`，内置男女音色预设，`--voice` 可覆盖
- 对齐策略：超长段 atempo 加速、偏短段轻微拉伸、间隙补静音；画面 stream-copy 不重编码
- 产出 `<视频名>_<lang>_dub.mp4`

## 完整管线（手动串）
```powershell
$d = ".\reference\<slug>"
# 1. 转录（中文走 FunASR，其他走 faster-whisper）
.\tools\.venv\Scripts\python.exe .\tools\transcribe_dispatch.py "$d\audio.wav" --lang auto
# 2. 翻译：把 $d\audio.srt 给我，指定目标语言，我产出 audio.<lang>.srt
# 4+5. 烧目标语言字幕 + 竖屏
.\.claude\skills\edit-ffmpeg\scripts\to_vertical.ps1 -Video "$d\video.mp4" -Out "$d\out_ja_9x16.mp4" -Mode captions -Subtitle "$d\audio.ja.srt"
```

## 翻译规则（我执行时遵守，参考 wjs-translating-subtitles）
- 字幕行 ≤ 15 中文字符 / ≤ 42 拉丁字符，超长拆行
- 中文去掉无指代功能的指示词（"这/那/那个"）
- 数字、日期、人名、品牌名保持准确
- 保持语气一致（口语→口语，正式→正式）
- TikTok 出海：不是直译，按目标语种平台的表达习惯改写标题/钩子

## 多语言矩阵（你的优势：中俄英日）
| 方向 | 转录引擎 | 翻译 | 配音(待补) | 字幕 |
|---|---|---|---|---|
| 中→俄/英/日 | FunASR zh | Claude | Edge TTS | edit-ffmpeg |
| 俄/英→中 | faster-whisper | Claude | Edge TTS zh | edit-ffmpeg |

## TODO（按需做，别提前堆）
- [x] `scripts/tts_dub.py`：Edge TTS 配音（免费、本地、中俄英日）✅
- [ ] `scripts/translate_srt.py`：若想脱离对话批量翻译，再接 Claude API
- [ ] 一键 localize.ps1：转录→（停下让我翻译）→配音→烧字幕→竖屏 串成一条命令
