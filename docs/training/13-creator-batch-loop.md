# Tutorial: localize a creator profile one video at a time

## Browser workflow

Start Video Graph Studio and select **Creator+Dub**. Paste a YouTube, Bilibili, Douyin, or TikTok creator URL; set a maximum item count; optionally provide a Netscape cookies file inside your Windows user profile; then choose languages, ASR device, translation device, and voices.

The four Graph steps are:

1. Creator Discovery commits ordered canonical video URLs.
2. Studio verifies the Creator Manifest fingerprint and coverage.
3. Creator Batch runs Source Intake, Transcription, Translation, Voice Rendering, and Localization for one creator item at a time.
4. Studio verifies every item, language, Localization Manifest, and MP4 derivative fingerprint.

## Resume behavior

If video 12 fails, later videos are still attempted. The batch remains `FAILED` and does not publish an aggregate manifest. Start the same run again after correcting access or connectivity: hash-verified completed videos are skipped, video 12 is retried with the same child operation IDs, and any stale output is rebuilt rather than trusted.

## Standalone workflow

```powershell
.\apps\creator-batch\run.ps1 localize C:\Jobs\creator-manifest.json `
  --target-language ru-RU --voice ru-RU=ru-RU-DmitryNeural `
  --output-dir C:\Jobs\creator-batch --operation-id batch-001 --json
```

The current evidence is domain verification with deterministic external adapters. Use a small `maxItems` value for the first live run before committing storage and time to a full creator profile.
