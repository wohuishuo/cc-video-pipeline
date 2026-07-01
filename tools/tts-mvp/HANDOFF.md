# TTS MVP 交付总结

> 给其他 AI 接手用的项目状态文档
> 生成时间: 2026-06-14
> 用户: 卡夏-Kasya (Windows 11, Intel Arc 140T/130T, 中文用户名 "艾莉")

## 1. 项目位置

```
C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\
```

跟 `.venv/` `remotion-hello/` `jianying-mcp/` **平级**，独立 MVP。

## 2. 全部已下载/已装的东西

### 2.1 Python 虚拟环境

- 路径: `tools/tts-mvp/.venv/`
- Python: 3.12.10
- 关键包:
  - `torch 2.12.0+xpu` ✅ (XPU 设备检测到 Intel Arc 130T 16GB，但 Qwen3-TTS 内部有 device 不一致 bug，**当前强制 CPU 跑**)
  - `qwen-tts 0.1.1` (PyPI)
  - `transformers`, `soundfile`, `huggingface_hub`
  - `modelscope 1.37.1` (Python API)
  - `datasets`, `pyarrow` (HF streaming)
  - `requests`, `parselmouth` (Praat 绑定, 评估用)
  - `noisereduce` (参考音频降噪)
  - `py7zr` (备用)

### 2.2 Qwen3-TTS 模型 (双模型)

| 模型 | 路径 | 大小 | 用途 |
|---|---|---|---|
| `Qwen3-TTS-12Hz-0.6B-CustomVoice` | `tools/tts-mvp/models/Qwen3-TTS-12Hz-0.6B-CustomVoice/` | 1.69GB | 9 个预设音色 (Vivian/Serena/Ono_Anna/Ryan/...) |
| `Qwen3-TTS-12Hz-0.6B-Base` | `tools/tts-mvp/models/Qwen3-TTS-12Hz-0.6B-Base/` | 1.69GB | VoiceClone (跨语言克隆) |

**注意**: Qwen3-TTS-Tokenizer-12Hz 是子模块, CustomVoice 自带。

### 2.3 参考音频库 (不入 git, 已 .gitignore)

| 目录 | 内容 | 大小 | 用途 |
|---|---|---|---|
| `voices/纳西妲_zh/ready/` | 298 个中文纳西妲游戏内 wav + 294 个 .lab 文本标签 | 167MB | 中→其他语言 克隆 |
| `voices/七七_zh/ready/` | 136 个中文七七游戏内 wav + 132 个 .lab | 65MB | 中→其他语言 克隆 |
| `voices/nahida_jp/raw/` | 日语纳西妲 wav (从 HF OpenSpeechHub/Genshin-Voice-Ja 60GB streaming 抓) | 增量 | 日→中 克隆 |
| `voices/nahida_zh_denoised/` | 用 noisereduce 降噪后的参考音频 (1 个样本) | 几 MB | 降噪实验 |
| `voices/preset_zh/` `voices/preset_ru/` | 空的 .gitkeep 占位 | 0 | 未来扩展 |

**所有 wav 来自用户 D 盘 `D:\BaiduNetdiskDownload\原神\【原神】须弥.7z` (937MB) 和 `【原神】璃月.7z` (1.3GB)**, 用 `scripts/extract_7z.py` 抽。

## 3. 工具脚本 (全部已入 git)

### 3.0 MVP 架构（2026-06-14 重构为可复用核心）

为了**给别的项目也用**，抽成可插拔双引擎 + HTTP 服务：

```
ttslib/            可复用核心包
  engines/base.py  TTSEngine 抽象（load/synth_preset/synth_clone/list_speakers/capabilities）
  engines/qwen.py  Qwen3-TTS 适配器（CustomVoice 预设 + Base 克隆，各懒加载一次）
  engines/sovits.py GPT-SoVITS 适配槽（接口留好，推理未接，接入步骤写在文件顶部）
  registry.py      get_engine("qwen" | "gpt-sovits")
  align.py         SRT/逐行 解析 + 时间对齐 + ffmpeg mux（dub 与 server 共用）
  langmap.py       语种/音色别名
server.py          FastAPI HTTP 服务，模型常驻（POST /tts /clone, GET /health /voices）
client_example.py  别的项目调用示例（urllib 零依赖）
```

**两种复用方式**：① 跨项目/跨语言 → 起 `server.py`，HTTP 调（不用共享 venv，模型只加载一次常驻）；
② 同 venv Python 项目 → `from ttslib import get_engine` 进程内调。
均已实测：/health loaded=true、/voices=9、POST /tts 落盘 OK；dub.py 经 ttslib 重构后 5.6s 出对齐 wav。

### 3.1 根目录工具

| 文件 | 用途 | 用法 |
|---|---|---|
| `server.py` | **HTTP 服务（跨项目复用入口）** | `python server.py [--engine qwen] [--port 8757]` |
| `dub.py` | **整段/SRT 配音 + 视频换音**（基于 ttslib） | `python dub.py --srt x.srt --lang ja --speaker anna --video in.mp4` |
| `client_example.py` | 别的项目怎么调 HTTP | 参考用 |
| `tts.py` | 预设音色配音（早期 CLI，仍可用） | `python tts.py --text "..." --lang zh --speaker vivian --out out.wav` |
| `cross_clone.py` | 跨语言 VoiceClone（早期 CLI，仍可用） | `python cross_clone.py --ref ref.wav --ref_text "..." --text "..." --lang Russian --out out.wav` |
| `fetch_voice.py` | 通用下载 (GitHub/HF/ModelScope/URL) | `python fetch_voice.py hf erythrocyte/... --out voices/...` |

### 3.2 scripts/ 工具 (8 个)

| 文件 | 用途 |
|---|---|
| `extract_7z.py` | 从原神 7z 抽指定角色 wav+lab, 平铺到 `<角色>_zh/ready/` |
| `pick_ref.py` | 按采样率/时长挑 ref_audio 候选 |
| `eval_clone.py` | 客观评估 clone 质量 (时长/RMS/F0/MFCC-DTW/高频占比) |
| `denoise_ref.py` | 用 noisereduce 降噪参考音频 (开头 0.3s 估噪声) |
| `peek_parquet.py` | 从 HF 数据集 streaming 抓指定 speaker 的 wav (省下 60GB 下载) |
| `hf_search.py` | 搜 HuggingFace 模型/数据集 |
| `hf_ls.py` | 列 HF 仓库文件树 |
| `hf_readme.py` | 读 HF 仓库 README |
| `list_aihobbyist.py` | 列 ModelScope 用户名下所有模型 |
| `aliyun_dump.py` | 抓阿里云盘分享 (发现 2 个 123 链接已失效) |

## 4. 已实测的功能

### 4.1 预设音色配音 (4 国语言)

| 文本 | 音色 | 输出 | 状态 |
|---|---|---|---|
| 你好世界 (11字中文) | Vivian | `outputs/test_zh.wav` 2.9s | ✅ |
| 36字中文 | Vivian | `outputs/test_zh2.wav` ~10s | ✅ |
| こんにちは世界 (日语) | Ono_Anna | `outputs/test_jp.wav` 3.4s | ✅ |
| Привет мир (俄语) | Ryan | `outputs/test_ru.wav` 3.2s | ✅ |
| Hello world (英语) | Ryan | `outputs/test_en.wav` 4.9s | ✅ |

**速度**: CPU 模式 30-60s 一段 (含 25s 模型加载)

### 4.2 跨语言 VoiceClone (4 个测试)

| 输入 | 输出 | 文件 |
|---|---|---|
| 中文纳西妲 ref → 俄语 | `clone_zh2ru.wav` 3.7s | ✅ |
| 中文纳西妲 ref → 日语 | `clone_zh2jp.wav` 3.0s | ✅ |
| 日语纳西妲 ref → 中文 | `clone_jp2zh.wav` 3.8s | ✅ |
| 日语纳西妲 ref → 俄语 | `clone_test_ru.wav` 3.7s | ✅ |

### 4.3 客观质量评估 (`eval_clone.py`)

⚠️ **克隆质量不理想**:
- 时长比 0.38-1.59x (理想 0.7-1.3x) — 时长对齐差
- MFCC-DTW 距离 100-130 (理想 < 50) — 音色距离大
- 高频损失 38-56% (理想 < 20%) — 听起来发闷

**降噪实验** (用 noisereduce 头部 0.3s 估噪声):
- 高频损失从 56% → 30% (改善)
- 但 MFCC 距离从 102 → 118 (反而变差)
- 时长比 0.47 → 0.64 (改善)

## 5. 已知坑

### 5.1 XPU 不可用
- 原因: Qwen3-TTS 0.1.1 在 Intel Arc XPU 上有 device 不一致 bug (`mem_get_info` 不支持 + generate 阶段 tensor 错位)
- 解决: `tts.py` 强制降 CPU (警告信息)
- 等: transformers 或 qwen-tts 修复

### 5.2 SoX 警告
- `pip install sox` 可消除, 不影响功能 (wav 处理已有 soundfile)

### 5.3 flash-attn 警告
- XPU/CUDA 才能用, CPU 下用 PyTorch 原生实现 (慢一点, 不影响功能)

### 5.4 PowerShell 中文路径
- PowerShell stdout 默认 GBK, 中文乱码
- 解决: 脚本里 `print(..., encoding="utf-8")` 或输出到文件
- 或者 `cmd /c` 跑 7z

### 5.5 删除长路径
- `Remove-Item -Recurse -Force` 在 PowerShell 7+ 对超长路径有时会保护路径错误
- 解决: `cmd /c rmdir /s /q <path>`

### 5.6 ModelScope Python 包
- `python -m modelscope` **不工作** (没有 `__main__`)
- 必须 `from modelscope import snapshot_download; snapshot_download(...)`

### 5.7 GitHub 空壳仓库
- HarutoLiang/Genshin-Nahida-Japanese-Voice (4KB, README only)
- AI-Hobbyist/Genshin_Datasets (1MB, README only)
- aihobbyist ModelScope 名下 7 个模型全部空壳
- 真音频在 MEGA / 阿里云盘 / ModelScope 都不在

### 5.8 GPT-SoVITS 模型不完整
- `D:\BaiduNetdiskDownload\so-vits4.0纳西妲模型\` 只有 `G_22400.pth` + `config.json`
- 缺 hubert/content_encoder 等关键依赖, **无法直接推理**
- 需要重训或找完整仓库

## 6. 可复用的脚本片段

### 6.1 跨语言克隆示例

```powershell
$py = "C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\.venv\Scripts\python.exe"
& $py "C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\cross_clone.py" `
  --ref "C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\voices\纳西妲_zh\ready\vo_dialog_LLZAQ004_nahida_01.wav" `
  --ref_text "这次太感谢你们了，请好好休息。累了可以去洗个澡上个厕所转换心情哦。" `
  --ref_lang Chinese `
  --text "Привет, я Нахида, добро пожаловать в Сумеру" `
  --lang Russian `
  --out "C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\outputs\clone_zh2ru.wav"
```

### 6.2 批量抽原神角色 wav

```powershell
$py = "C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\.venv\Scripts\python.exe"
& $py "C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\scripts\extract_7z.py" "纳西妲" "D:\BaiduNetdiskDownload\原神\【原神】须弥.7z"
& $py "C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\scripts\extract_7z.py" "七七"   "D:\BaiduNetdiskDownload\原神\【原神】璃月.7z"
& $py "C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\scripts\extract_7z.py" "甘雨"   "D:\BaiduNetdiskDownload\原神\【原神】璃月.7z"
& $py "C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\scripts\extract_7z.py" "胡桃"   "D:\BaiduNetdiskDownload\原神\【原神】璃月.7z"
& $py "C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\scripts\extract_7z.py" "可莉"   "D:\BaiduNetdiskDownload\原神\【原神】蒙德.7z"
& $py "C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\scripts\extract_7z.py" "八重神子" "D:\BaiduNetdiskDownload\原神\【原神】稻妻.7z"
```

### 6.3 评估克隆质量

```powershell
$py = "C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\.venv\Scripts\python.exe"
& $py "C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\scripts\eval_clone.py" `
  "C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\voices\纳西妲_zh\ready\vo_dialog_LLZAQ004_nahida_01.wav" `
  "C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\outputs\clone_zh2ru.wav"
```

### 6.4 降噪参考音频

```powershell
$py = "C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\.venv\Scripts\python.exe"
& $py "C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\scripts\denoise_ref.py" `
  "C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\voices\纳西妲_zh\ready\vo_dialog_LLZAQ004_nahida_01.wav" `
  "C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\voices\nahida_zh_denoised\vo_dialog_LLZAQ004_nahida_01.wav"
```

## 7. 提交历史

```
3ff4bb7 feat(tts-mvp): 跨语言 VoiceClone + 纳西妲/七七参考音频库 (12 files, 584 insertions)
95504e6 feat(tts-mvp): 独立 TTS MVP (Qwen3-TTS) (9 files, 309 insertions)
```

## 8. 接下来可做 (没做的)

1. **听 4 个 clone wav** —— 客观指标差但听感可能 OK
2. **换 1.7B Base 模型** —— `Qwen/Qwen3-TTS-12Hz-1.7B-Base`, 慢 2-3x 但更准
3. ~~**接 P2 剪辑流水线**~~ ✅ **已完成 (2026-06-14)** —— `dub.py` 把单句 wav 补成
   "整条视频换音": 模型只加载一次, 逐句合成后按 SRT/逐行时间轴对齐 (间隙补静音/
   超长 atempo 加速/偏短拉伸), mux 回视频 (画面 stream-copy)。支持预设音色与
   `--clone` 跨语言克隆。已实测 2 行中文稿 → 6.7s 对齐 wav 通过。用法见 README。
4. **等 XPU bug 修** —— 速度上去了再调
5. **更多角色** —— 跑 `extract_7z.py` 抽其他角色 (甘雨/胡桃/可莉/八重神子/...)
6. **日语音频继续下** —— `voices/nahida_jp/raw/` 后台 streaming 任务还在跑, 应该还在累积

## 9. 一键环境检查

```powershell
# 跑一下确认环境正常
$py = "C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\.venv\Scripts\python.exe"
& $py -c "import torch, qwen_tts, modelscope, soundfile, parselmouth, noisereduce; print('all ok'); print('torch:', torch.__version__); print('xpu:', torch.xpu.is_available())"
```

期望输出:
```
all ok
torch: 2.12.0+xpu
xpu: True
```

## 10. 已知优秀资源 (供扩展)

| 资源 | URL/位置 | 价值 |
|---|---|---|
| OpenSpeechHub/Genshin-Voice-Ja | HF dataset, 60GB, 109630 句日语原神 | streaming 抓纳西妲 |
| hanamizuki-ai/genshin-voice-v3.4-mandarin | HF dataset, 30GB, 1401 下载 | 抓中文原神全角色 |
| simon3000/genshin-voice | HF dataset, 200GB (太大) | 中文全角色 (慎用) |
| `D:\BaiduNetdiskDownload\原神\*.7z` | 本地 6.6GB, 7 个区域 7z | 推荐用 extract_7z.py 抽 |
| Akjava/QWEN3-TTS-Voice-Clone-100-Japanese-Female-ITA-Corpus-Emotion | HF dataset, 100 个女声 24kHz wav | **专用 Qwen3-TTS 训练用**, 不适合纳西妲克隆 |
| erythrocyte/AI-Hobbyist (CSDN 用户) | ModelScope | GPT-SoVITS V2 原神/星铁/鸣潮 |

## 11. 给接手 AI 的提示

- **环境** `tools/setup.ps1` 检测的是 `tools/.venv` (FunASR/Whisper 用的), **跟 TTS MVP 的 `tools/tts-mvp/.venv` 是两个独立 venv**
- **CLAUDE.md** 第 1 行就是这个项目根, TTS 工具单独在 tools/tts-mvp/
- **PowerShell 中文路径问题**: 脚本和命令里中文路径要用绝对路径+引号
- **git 操作**: `tts-mvp` 已经按目录 .gitignore, 大文件不入版本控制
- **优先任务**: 让用户**听 4 个 clone wav** 判断质量, 再决定换 1.7B 模型还是接受现状

---

**总结**: TTS MVP 跑通了 9 音色 + 4 国语言预设配音, 跨语言 VoiceClone 跑通但客观质量待用户主观评估。298+136 个游戏内 wav 已就位, 工具栈完整。XPU 暂不可用, 强制 CPU。提交 2 个 commit, 12 个新文件。
