# Voice Rendering MVP

Voice Rendering consumes a verified Translation Manifest and produces one hash-bound MP3 per translated segment. It processes one clip at a time, checkpoints every success and resumes without regenerating still-valid clips.

```powershell
.\apps\voice-rendering\run.ps1 C:\work\translation-manifest.json `
  --output-dir C:\work\voice `
  --operation-id voice-001 `
  --voice ru-RU=ru-RU-DmitryNeural `
  --voice en-US=en-US-GuyNeural `
  --json
```

This app renders named voices. It does not clone a voice, change translation wording, mix audio, stretch timing, burn subtitles, compose video or upload media.
