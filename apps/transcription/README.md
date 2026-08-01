# Transcription MVP

Transcription consumes a committed Source Intake manifest and publishes timestamped transcript JSON/SRT artifacts plus a `transcript-manifest.json` and `transcription-receipt.json`.

```powershell
.\install.ps1
.\run.ps1 C:\Jobs\intake\source-manifest.json `
  --output-dir C:\Jobs\transcripts `
  --operation-id job-42 `
  --language auto `
  --model small `
  --device auto `
  --json
```

The loop handles one media item at a time. Completed item checkpoints are verified and reused after a later item fails. Reusing an operation ID with changed source, language, model, device or compute policy conflicts instead of overwriting prior evidence.

Faster Whisper is a replaceable adapter. Model files are cached outside Git. Transcription does not own translation, synthesize speech, style subtitles, mix audio or publish video.
