# TTS MVP — Qwen3-TTS 本地配音

> **独立 MVP**，跟 .venv / remotion-hello / jianying-mcp 平级，
> 不污染现有 P0-P2 流水线。给 cos 跳舞/Vlog/科普口播做 AI 配音。

## 当前状态

- 引擎：Qwen3-TTS 官方 Python 版（`qwen-tts` PyPI）
- 模型：Qwen3-TTS-12Hz-0.6B-CustomVoice（9 个预设音色）✅ 已下载（1.69GB）
- 设备：~~Intel Arc 140T XPU~~ **当前强制 CPU**（XPU 路径有 device 不一致 bug，待 transformers 修复）
- 语种：10 国（中/英/日/韩/德/法/俄/葡/西/意）
- **本机实测速度**（2026-06-14，CPU 模式）：
  - 11 字中文 → 2.9s 音频（耗时 ~30s 算加载）
  - 36 字中文 → ~10s 音频（耗时 42s 算加载）
  - 13 字日语/19 字俄语/28 字英语 → 3-5s 音频

## 目录结构

```
tools/tts-mvp/
  .venv/                                  ← 独立 venv (torch+xpu + qwen-tts)
  models/
    Qwen3-TTS-12Hz-0.6B-CustomVoice/      ← 主模型
    Qwen3-TTS-Tokenizer-12Hz/             ← Tokenizer (CustomVoice 自带可不下载)
  outputs/                                ← 默认输出目录
  voices/                                 ← 声线参考音频（待填）
    nahida_jp/                            ← 计划放纳西妲参考音频
    preset_zh/                            ← 中文预设
    preset_ru/                            ← 俄语预设
  tts.py                                  ← CLI 工具脚本
  README.md                               ← 本文件
```

## 预设音色速查

| 简写 | 全名 | 母语 | 简介 |
|---|---|---|---|
| `vivian` | Vivian | 中文 | Bright, slightly edgy young female ⭐ 主声 |
| `serena` | Serena | 中文 | Warm, gentle young female |
| `uncle` | Uncle_Fu | 中文 | 中年男声 |
| `dylan` | Dylan | 中文(京腔) | Beijing 男声 |
| `eric` | Eric | 中文(川话) | Chengdu 男声 |
| `ryan` | Ryan | 英文 | Dynamic English male |
| `aiden` | Aiden | 英文 | American male |
| `anna` / `nahida` | Ono_Anna | 日语 | Playful Japanese female ⭐ 纳西妲替代 |
| `sohee` | Sohee | 韩语 | Warm Korean female |

## 用法

### 1. 配音一句话

```powershell
.\.venv\Scripts\python.exe .\tts.py `
  --text "你好世界" `
  --lang zh --speaker vivian `
  --out outputs\hello_zh.wav
```

### 2. 日语 Cos 纳西妲声线（用 Ono_Anna 预设）

```powershell
.\.venv\Scripts\python.exe .\tts.py `
  --text "草神です、よろしくお願いします" `
  --lang jp --speaker anna `
  --out outputs\cos_nahida.wav
```

### 3. 俄语科普配音

```powershell
.\.venv\Scripts\python.exe .\tts.py `
  --text "Привет, это тестовая фраза" `
  --lang ru --speaker ryan `
  --out outputs\ru_test.wav
```

### 4. 加情感控制

```powershell
.\.venv\Scripts\python.exe .\tts.py `
  --text "你怎么能这样做" `
  --lang zh --speaker vivian `
  --instruct "用特别愤怒的语气说" `
  --out outputs\angry.wav
```

## 常用参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `--text` | (必填) | 要合成的文本 |
| `--lang` | Chinese | zh/jp/en/ru/cn... 见上 |
| `--speaker` | Vivian | 见上音色表 |
| `--instruct` | "" | 情感/语气控制词 |
| `--out` | outputs/out.wav | 输出路径 |
| `--device` | xpu | xpu/cpu/cuda |
| `--model` | 默认 CustomVoice 路径 | 本地模型目录 |

## 接入现有流水线

配音输出 wav 后，可直接接 P2 剪辑：

```powershell
# 1. tts 生成配音
.\.venv\Scripts\python.exe .\tts.py --text "..." --out projects\cos-2026-07\voice.wav

# 2. ffmpeg 合成画面+配音
ffmpeg -i projects\cos-2026-07\video.mp4 -i projects\cos-2026-07\voice.wav `
       -c:v h264_qsv -c:a aac -shortest `
       projects\cos-2026-07\final.mp4
```

## 性能预期（Intel Arc 140T / 当前 CPU 实测）

| 文本长度 | 音频长度 | 耗时（含模型加载） |
|---|---|---|
| 11 字 | 2.9s | ~30s |
| 36 字 | ~10s | ~42s |
| 100 字 | ~30s | 预计 60-90s |

> **模型加载固定 ~25s**（CPU 加载 safetensors），生成时间随文本线性增长。
> 长稿可分多次跑、或后续用 batch API 减少加载次数。
>
> XPU 模式理论能快 3-5 倍，但 Qwen3-TTS 0.1.1 + transformers 暂有兼容 bug。等修复后切回。

## 故障排查

### `ModuleNotFoundError: qwen_tts`
→ 用 `.venv\Scripts\python.exe`，**不要**用系统 Python 或 `tools/.venv`。
当前 `tools/.venv` 是 CPU 版的 torch+FunASR，不兼容 qwen-tts 的 XPU 加速。

### `[warn] torch.xpu 不可用`
→ Intel 驱动没装好或 torch+xpu 包装错。检查：
```powershell
.\.venv\Scripts\python.exe -c "import torch; print(torch.__version__); print(torch.xpu.is_available())"
```
需要 `torch 2.4+` 且 `intel-extension-for-pytorch`（XPU wheel 内置）。

### 模型下载失败
→ 手动从 ModelScope 拉：
```powershell
.\.venv\Scripts\python.exe -m modelscope download `
  --model Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice `
  --local_dir models\Qwen3-TTS-12Hz-0.6B-CustomVoice
```

## TODO

- [ ] 实测 XPU vs CPU 速度，填进性能表
- [ ] 加 `--batch` 模式（按行读 stdin 出多段）
- [ ] 接 VoiceClone：找一段纳西妲参考音频 → `voices/nahida_jp/` → 用 `generate_voice_clone` API
- [ ] 评估 1.7B 模型（更高质量，CPU 上慢 2x）
