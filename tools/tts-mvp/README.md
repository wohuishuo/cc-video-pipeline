# TTS MVP — 本地 TTS 复用核心（Qwen3-TTS + GPT-SoVITS 槽）

> **独立 MVP**，跟 .venv / remotion-hello / jianying-mcp 平级，不污染现有 P0-P2 流水线。
> 给本项目（cos/Vlog/科普配音）**和别的项目**共用：引擎可插拔，HTTP 接口跨项目调。

## 架构（可插拔双引擎 + HTTP 服务）

```
ttslib/                  ← 可复用核心（别的项目 import 它，或走 HTTP）
  engines/
    base.py              ← TTSEngine 抽象：load / synth_preset / synth_clone / list_speakers
    qwen.py              ← Qwen3-TTS 适配器（CustomVoice 预设 + Base 克隆，各加载一次）
    sovits.py            ← GPT-SoVITS 适配槽（接口留好，推理待接，见文件内步骤）
  registry.py            ← get_engine("qwen" | "gpt-sovits")
  align.py               ← SRT/逐行 解析 + 时间对齐 + ffmpeg mux
  langmap.py             ← 语种/音色别名归一
server.py                ← FastAPI HTTP 服务（模型常驻，POST /tts /clone）
client_example.py        ← 别的项目怎么调（urllib，零依赖）
dub.py                   ← 整段/SRT 配音 + 视频换音（基于 ttslib）
tts.py / cross_clone.py  ← 早期单句 CLI（仍可用；新代码走 ttslib/server）
```

## 跨项目复用：起一个 HTTP 服务即可

别的项目**不用共享 venv、不用每次加载模型**（模型常驻，省掉每次 25s）：

```powershell
# 本项目这边起服务（启动加载一次后常驻）
.\.venv\Scripts\python.exe server.py            # 默认 qwen, http://127.0.0.1:8757
```

```python
# 别的项目（任意 venv / 任意语言）这样调：
import urllib.request, json
req = urllib.request.Request("http://127.0.0.1:8757/tts",
    data=json.dumps({"text":"你好","lang":"zh","speaker":"vivian"}).encode(),
    headers={"Content-Type":"application/json"})
open("out.wav","wb").write(urllib.request.urlopen(req).read())   # 直接拿 wav 字节
```

接口：`GET /health` · `GET /voices` · `POST /tts {text,lang,speaker,instruct?}` ·
`POST /clone {text,lang,ref_audio,ref_text,ref_lang?}`。两个 POST 加 `?save=路径` 可让
服务端直接落盘返回 `{path,duration,sr}`。完整示例见 `client_example.py`。

> 同 venv 的 Python 项目也可直接 `from ttslib import get_engine` 进程内调用。

## 切引擎

`server.py --engine qwen`（现可用）/ `--engine gpt-sovits`（接口已留，待接入完整权重）。
GPT-SoVITS 接入步骤写在 `ttslib/engines/sovits.py` 顶部——主打少样本高保真克隆，
和 Qwen 的开箱预设音色互补，所以做成可切换。

---


## 当前状态

- 引擎：Qwen3-TTS 官方 Python 版（`qwen-tts` PyPI）
- 模型：
  - `Qwen3-TTS-12Hz-0.6B-CustomVoice`（9 个预设音色）✅ 已下载 1.69GB
  - `Qwen3-TTS-12Hz-0.6B-Base`（VoiceClone 能力）✅ 已下载 1.69GB
- 设备：~~Intel Arc 140T XPU~~ **当前强制 CPU**（XPU 路径有 device 不一致 bug，待 transformers 修复）
- 语种：10 国（中/英/日/韩/德/法/俄/葡/西/意）
- **参考音频库**：
  - `voices/纳西妲_zh/ready/` — 298 个中文纳西妲游戏内语音 (167MB)
  - `voices/七七_zh/ready/` — 136 个中文七七游戏内语音 (65MB)
  - `voices/nahida_jp/raw/` — 日语纳西妲 (streaming 下载, 进行中)
- **本机实测速度**（2026-06-14，CPU 模式）：
  - 11 字中文 → 2.9s 音频（耗时 ~30s 算加载）
  - 36 字中文 → ~10s 音频（耗时 42s 算加载）
  - 13 字日语/19 字俄语/28 字英语 → 3-5s 音频
  - 跨语言 VoiceClone: zh→ru / zh→jp / jp→zh 全部 3-4s 输出

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

## 跨语言 VoiceClone（纳西妲/七七专用）

原理：用 3-15 秒参考音频（含真实文本）+ Qwen3-TTS Base 模型，
**让模型用参考声线说另一种语言的文本**。

```powershell
# 1. 中→俄: 用中文纳西妲说俄语
.\.venv\Scripts\python.exe .\cross_clone.py `
  --ref voices\纳西妲_zh\ready\vo_dialog_LLZAQ004_nahida_01.wav `
  --ref_text "这次太感谢你们了，请好好休息。累了可以去洗个澡上个厕所转换心情哦。" `
  --ref_lang Chinese `
  --text "Привет, я Нахида, добро пожаловать в Сумеру" `
  --lang Russian `
  --out outputs\clone_zh2ru.wav

# 2. 日→中: 用日语纳西妲说中文
.\.venv\Scripts\python.exe .\cross_clone.py `
  --ref voices\nahida_jp\raw\voice_326_気を付けて。何か出てきたわ！.wav `
  --ref_text "気を付けて。何か出てきたわ！" `
  --ref_lang Japanese `
  --text "你好，欢迎来到须弥，我是纳西妲" `
  --lang Chinese `
  --out outputs\clone_jp2zh.wav
```

参考音频质量要求：
- 时长 3-15 秒最佳（太长 Qwen3-TTS 会截断）
- 单声道 (ch=1) 优先
- 48kHz/24kHz Qwen3-TTS 内部 resample
- **ref_text 必须与 wav 实际发音一致**（否则克隆失败）

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

## 整段配音 / 视频换音（dub.py）— ✅ 已完成

`tts.py`/`cross_clone.py` 只出单句 wav，`dub.py` 把它补成"整条视频换音"：
**模型只加载一次**，逐句合成后按时间轴对齐（间隙补静音/超长加速/偏短拉伸），mux 回视频。

```powershell
$py = ".\.venv\Scripts\python.exe"

# 1) 逐行稿子配音（口播/科普）—— 顺序拼 + 句间停顿
$py .\dub.py --lines script.txt --lang zh --speaker vivian --gap 0.35 --out outputs\narration.wav

# 2) SRT 时间对齐换音（本地化现有视频）
$py .\dub.py --srt in.ja.srt --lang ja --speaker anna --video in.mp4
#   -> in_ja_dub.mp4（画面 stream-copy，只换音轨）

# 3) 跨语言克隆 + 视频换音（纳西妲声线说日语，对齐到视频）
$py .\dub.py --srt in.ja.srt --lang ja --clone `
  --ref voices\纳西妲_zh\ready\vo_dialog_LLZAQ004_nahida_01.wav `
  --ref_text "这次太感谢你们了，请好好休息。" --ref_lang zh `
  --video in.mp4
```

| 参数 | 说明 |
|---|---|
| `--srt` / `--lines` | 二选一：SRT 时间对齐 / 逐行稿子顺序拼 |
| `--video` | 给了就 mux 回视频（不给只出对齐音轨 wav） |
| `--speaker` | 预设音色；或 `--clone --ref --ref_text` 走克隆 |
| `--gap` | 逐行模式句间停顿秒（默认 0.35） |
| `--keep-temp` | 保留分句 wav 供检查 |

> 已实测：2 行中文稿 → 6.7s 对齐 wav，模型单次加载，对齐正确。

## TODO

- [ ] 实测 XPU vs CPU 速度，填进性能表
- [x] ~~整段/SRT 配音 + 视频换音~~ → `dub.py` 已完成
- [x] ~~接 VoiceClone~~ → `cross_clone.py` + `dub.py --clone`
- [ ] 评估 1.7B 模型（更高质量，CPU 上慢 2x）
