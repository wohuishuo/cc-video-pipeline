# Localization MVP

Localization consumes three explicit committed facts—Source Manifest, Translation Manifest and Voice Manifest—and produces subtitle-burned, dubbed MP4 derivatives. It processes one language/media job at a time and checkpoints every probe-verified output.

```powershell
.\apps\localization\run.ps1 `
  C:\work\source-manifest.json `
  C:\work\translation-manifest.json `
  C:\work\voice-manifest.json `
  --output-dir C:\work\localized `
  --operation-id localization-001 `
  --source-volume 0.12 `
  --json
```

The v1 policy burns translated SRT, aligns every voice clip to its segment start, speeds up only clips that exceed their segment window, mixes source audio at volume `0.12`, and publishes H.264/AAC MP4 only after FFprobe verification.

Localization does not translate text, synthesize or clone voices, discover sources, separate original vocals or upload videos. Legacy `localizer/` modules remain compatibility code and are not imported by this public path.
