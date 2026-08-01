# Translation MVP

Translation converts a verified `transcript-manifest.json` into editable multilingual JSON and SRT artifacts. It processes one work item at a time, checkpoints after every item and can resume without translating verified completed work again.

## Run

```powershell
.\apps\translation\install.ps1
.\apps\translation\run.ps1 C:\work\transcript-manifest.json `
  --output-dir C:\work\translation `
  --operation-id translation-001 `
  --target-language ru-RU `
  --target-language en-US `
  --device auto `
  --batch-size 8 `
  --json
```

Supported target language policies are `ru-RU`, `en-US` and `kk-KZ`. Short forms `ru`, `en` and `kk` normalize to those values. The default production adapter is local Meta NLLB and loads lazily when the first item begins.

## Owned artifacts

- `translation-receipt.json`: durable operation/checkpoint truth.
- `translation-manifest.json`: exact media/language coverage and artifact fingerprints.
- `items/*/translation.json`: source text, translated text, timing and review state.
- `items/*/translation.srt`: editable subtitle projection.

Machine translations are explicitly marked `MACHINE`. This capability does not synthesize a voice, clone a voice, burn subtitles into video, mix audio or upload media. Those are downstream MVPs.
