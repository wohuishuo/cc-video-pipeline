# Creator Batch MVP

Consume one verified Creator Manifest and localize every canonical video URL one at a time. The batch owns only continuation state; Source Intake, Transcription, Translation, Voice Rendering, and Localization continue to own their artifacts.

```powershell
.\apps\creator-batch\run.ps1 localize C:\Jobs\creator-manifest.json `
  --target-language ru-RU --voice ru-RU=ru-RU-DmitryNeural `
  --target-language en-US --voice en-US=en-US-GuyNeural `
  --cookies C:\Private\cookies.txt `
  --output-dir C:\Jobs\creator-localized `
  --operation-id creator-batch-001 --json
```

Exactly one item and one child owner run at a time. A failed item is checkpointed and later items are still attempted. Rerunning the identical operation skips completed items whose Localization Manifest hashes still match and retries only incomplete or stale items. Changed inputs under the same operation ID are rejected.

Cookie contents and paths never enter the receipt or aggregate manifest. The cookie path is passed only to the Source Intake child command for the current item.
