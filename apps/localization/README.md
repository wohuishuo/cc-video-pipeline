# Localization MVP

Localization consumes three explicit committed facts—Source Manifest, Translation Manifest and Voice Manifest—and produces subtitle-burned, dubbed MP4 derivatives. It processes one language/media job at a time and checkpoints every probe-verified output.

Delivery level: `PLATFORM_INTEGRATED`. The public launcher and the complete ten-step Graph Studio workflow have produced real RU/KK FFmpeg derivatives and verified them with FFprobe and SHA-256.

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

## Composition policy

- Voice clips are aligned to committed segment start times.
- Only clips longer than their segment window are tempo-adjusted.
- Original audio is retained at `--source-volume` (default `0.12`); this is attenuation, not vocal separation.
- Committed SRT subtitles are burned into the output.
- A derivative is published only after FFprobe reports positive duration and dimensions plus video and audio codecs.
- Retries reuse only derivatives whose fingerprints and lineage still match.
