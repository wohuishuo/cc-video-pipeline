# Voice Rendering MVP

Voice Rendering consumes a verified Translation Manifest and produces one hash-bound audio clip per translated segment. It processes one clip at a time, checkpoints every success and resumes without regenerating still-valid clips. The provider is explicit:

- `edge` — Edge TTS named voices, MP3 output.
- `qwen3` — local Qwen3-TTS preset voices, WAV output and one resident model per video.
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

Qwen3-TTS uses the repository-local `tools/tts-mvp` runtime and model store:

```powershell
.\apps\voice-rendering\run.ps1 C:\work\translation-manifest.json `
  --output-dir C:\work\qwen-voice `
  --operation-id voice-qwen-001 `
  --provider qwen3 --qwen-device cpu `
  --voice ru-RU=Ryan `
  --json
```

This app renders named or timing voices. It does not clone a voice, change translation wording, mix audio, stretch timing, burn subtitles, compose video or upload media.
