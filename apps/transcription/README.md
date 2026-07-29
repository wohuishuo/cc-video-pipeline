# Transcription MVP

Converts one media file into transcript JSON and SRT. The dispatcher selects FunASR for Chinese and faster-whisper for other languages.

```powershell
.\install.ps1
.\run.ps1 input.wav --lang auto
```

Model downloads are cached outside Git.
