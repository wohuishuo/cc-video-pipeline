---
name: local-tts-dub
description: 使用本机 Qwen3-TTS 做预设音色、纳西妲跨语言克隆、整稿/SRT/视频配音，并在稳定 CPU 生产版与 Transformers 5 + Intel Arc XPU 实验版之间安全路由。用户说“配音、朗读、纳西妲说中文/英文/日语/俄语、TTS、Qwen3-TTS、XPU/GPU 加速、预热或测速”时使用。
---

# 本地 TTS 配音

## 先做路由

1. **要可靠成片、长文朗读或批处理**：使用 `tools/tts-mvp` 稳定生产版，设备选 CPU。
2. **只做预设音色单句**：使用 `tts.py`。
3. **纳西妲/七七声线或跨语言**：使用 Base 模型的 `cross_clone.py`；整稿使用 `dub.py --clone`。
4. **已有 SRT 或要替换视频音轨**：使用 `dub.py --srt ... --video ...`。
5. **研究 Transformers 5/XPU/torch.compile**：只使用 `projects/qwen3-tts-xpu-v5-fork`。先读 [references/xpu-experiment.md](references/xpu-experiment.md)，不得覆盖生产环境。

先运行：

```powershell
.\.claude\skills\local-tts-dub\scripts\check.ps1
```

## 稳定生产命令

在 `tools/tts-mvp` 目录运行，必须使用其 Python 3.12 独立环境：

```powershell
cd tools\tts-mvp
$py = '.\.venv\Scripts\python.exe'
```

### 纳西妲单句跨语言克隆

```powershell
$ref = 'voices\纳西妲_zh\ready\vo_dialog_LLZAQ004_nahida_01.wav'
$refText = '这次太感谢你们了，请好好休息。累了可以去洗个澡上个厕所转换心情哦。'
$py .\cross_clone.py --ref $ref --ref_text $refText `
  --text 'Hello, welcome to the lesson.' --lang en --out outputs\nahida_en.wav
```

把 `--lang` 改成 `zh`、`ja`、`ru` 即可。参考文本必须与参考音频完全一致。

### 整稿和视频配音

```powershell
# 一行一句；模型只加载一次
$py .\dub.py --lines script.txt --lang zh --clone `
  --ref $ref --ref_text $refText --gap 0.35 --out outputs\narration.wav

# 按 SRT 时间轴配音并换入视频
$py .\dub.py --srt captions.en.srt --lang en --clone `
  --ref $ref --ref_text $refText --video input.mp4 --out output_en.mp4
```

中英日俄混合稿不能用单个 `dub.py --lang`。应把文本拆成带 `lang` 的片段，在同一 Python 进程内调用 `get_engine('qwen')`，逐段 `synth_clone()`，最后复用 `ttslib.align.mux()`；不要为每句启动一次 Python。

## Transformers 5 / Intel XPU 实验

当前只适合测速和修复，**不适合成片**：Transformers 5 分支仍有 EOS 不停止问题。`128 tokens` 是固定长度吞吐测试，不是生产限制。

```powershell
# eager 基准
.\projects\qwen3-tts-xpu-v5-fork\run_benchmark.ps1 -Case short -Rounds 2 -MaxTokens 128

# torch.compile：首次约数分钟；同一进程后续最快
.\projects\qwen3-tts-xpu-v5-fork\run_benchmark.ps1 -Case short -Compile -Rounds 2 -MaxTokens 128
```

遵守以下规则：

- 不安装普通 PyPI CPU Torch 到实验环境；XPU Torch 版本必须带 `+xpu`。
- 不用系统 Python 3.14。
- 不把 Transformers 5 装进 `tools/tts-mvp/.venv`。
- 不把固定 128-token 输出当成完整句子或音质结论。
- `torch.compile` 不是安装后永久完成：同一常驻进程、已见过的输入形状才会热复用；重启仍需预热。
- 阅读 App 应调用常驻 HTTP 服务，并在启动时预热常见长度桶，绝不能逐句拉起 Python。
- CPU+GPU+NPU 不能把同一次自回归生成简单相加。当前关键路径用 XPU；CPU负责文本、音频和服务调度。NPU 需要 OpenVINO 模型转换，当前 Qwen3-TTS 动态生成链尚不能直接加入。

## 交付前检查

- 听首句、最长句、英文句和结尾句，确认无复读、截断、爆音。
- 检查音频时长；异常长句必须设置生成上限并单独重试。
- 长稿保留逐段 WAV 和时间轴，失败后从断点继续，不重跑全稿。
- 成片默认走稳定 CPU 路径，除非实验分支已通过 EOS、音质 AB、长文连续生成三项验证。
