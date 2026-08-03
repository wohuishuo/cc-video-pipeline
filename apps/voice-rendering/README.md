# Voice Rendering MVP

Voice Rendering consumes a verified Translation Manifest and produces one hash-bound audio clip per translated segment. It checkpoints completed work and resumes without regenerating still-valid clips. The provider is explicit:

- `edge` — Edge TTS named voices, MP3 output.
- `qwen3` — local Qwen3-TTS preset voices, WAV output, one resident CUDA model and batches of eight independent subtitle clips.
- `original` — timed silence clips so Localization preserves original audio and burns translated subtitles without synthetic speech.

```powershell
.\apps\voice-rendering\run.ps1 C:\work\translation-manifest.json `
  --output-dir C:\work\voice `
  --operation-id voice-001 `
  --provider edge `
  --voice ru-RU=ru-RU-DmitryNeural `
  --voice en-US=en-US-GuyNeural `
  --json
```

Qwen3-TTS uses the repository-local runtime and Hugging Face model cache:

```powershell
.\apps\voice-rendering\run.ps1 C:\work\translation-manifest.json `
  --output-dir C:\work\qwen-voice `
  --operation-id voice-qwen-001 `
  --provider qwen3 --qwen-device auto `
  --voice ru-RU=Ryan `
  --json
```

Qwen batching does not merge narration into one long track. One model call accepts up to eight texts and returns eight separate waveforms, so each output keeps the exact original subtitle segment ID and time window. If a GPU batch fails, only that batch falls back to independent serial synthesis.

On the local RTX 4070 Laptop GPU, the complete real 129-segment Russian translation finished in 285.18 seconds with zero failed clips. The previous serial implementation spent 1,352.38 seconds in the same Voice Rendering stage, so the end-to-end voice stage is 4.74x faster. A focused eight-item batch took 12.43 seconds (1.55 seconds per item), compared with 8.88 seconds per item after initialization in the old loop. PyTorch SDPA, CUDA and bfloat16 are already active. The optional SoX and external `flash-attn` warnings are not download requirements and were not the cause of the serial slowdown.

This app renders named or timing voices. It does not clone a voice, change translation wording, mix audio, stretch timing, burn subtitles, compose video or upload media.
