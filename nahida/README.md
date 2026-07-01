# Nahida so-vits voice conversion

This folder contains a so-vits-svc 4.x Nahida voice-conversion setup.

Important: so-vits-svc is not text-to-speech. It converts an existing source
voice/audio into the target voice. The practical pipeline is:

1. Generate a source voice with edge-tts or another TTS.
2. Run so-vits-svc conversion with the Nahida model.
3. Use the output wav in the video pipeline.

## One-command use

From the repository root:

```powershell
.\tools\tts-mvp\nahida_sovits.ps1 `
  -Text "你好，旅行者。我是纳西妲。" `
  -Out .\nahida\sovits\outputs\nahida_demo.wav
```

Use an existing audio file instead:

```powershell
.\tools\tts-mvp\nahida_sovits.ps1 `
  -InputAudio .\nahida\sovits\input\test_zh.mp3 `
  -Out .\nahida\sovits\outputs\test_zh_nahida.wav
```

Batch a long Markdown script into one narration wav:

```powershell
python .\tools\tts-mvp\nahida_sovits_batch.py `
  --script .\projects\information-gap-business\script.md `
  --out .\projects\information-gap-business\audio\information-gap-nahida-sovits.wav `
  --max-chars 1800
```

## Installed pieces

- Runtime: `tools/tts-mvp/.venv`
- CLI package: `so-vits-svc-fork`
- Source TTS for `-Text`: `tools/.venv` + `edge-tts`
- Model/config:
  - `nahida/sovits/logs/44k/G_40000.pth`
  - `nahida/sovits/configs/44k/config.json`
  - speaker id: `nahida`
- ContentVec encoder cache:
  - `C:\Users\艾莉\.cache\huggingface\hub\models--lengyue233--content-vec-best`

## Notes

- The original `.pth` files were PyTorch zip checkpoints. Do not expand them;
  use the `.zip` payload copied/renamed as `.pth`.
- The first successful run downloaded the ContentVec encoder. The script now
  defaults to offline mode for so-vits conversion to avoid slow Hugging Face
  retry probes. Use `-Online` only when refreshing model cache.
- CPU conversion is already quick for short spoken clips. The slow part is
  source TTS if you choose a slower generator.
