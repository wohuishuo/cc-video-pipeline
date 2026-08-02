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
  --provider nllb `
  --device auto `
  --batch-size 8 `
  --json
```

The public language contract currently contains 20 searchable locales. The default production adapter is local Meta NLLB and loads lazily when the first item begins.

For quality-first cloud translation, set the credential only in the process environment and choose DeepSeek. The credential is never accepted as a command argument, written to receipts or included in adapter identity.

```powershell
$env:DEEPSEEK_API_KEY = "your-key"
.\apps\translation\run.ps1 C:\work\transcript-manifest.json `
  --output-dir C:\work\translation-deepseek `
  --operation-id translation-deepseek-001 `
  --target-language ru-RU `
  --provider deepseek `
  --model deepseek-v4-flash `
  --json
```

Both adapters publish exactly the same Translation Manifest contract. DeepSeek responses must contain exactly one non-empty translated string for every source subtitle segment; malformed or partial coverage is retried a bounded number of times and then fails without publishing a manifest.

## Owned artifacts

- `translation-receipt.json`: durable operation/checkpoint truth.
- `translation-manifest.json`: exact media/language coverage and artifact fingerprints.
- `items/*/translation.json`: source text, translated text, timing and review state.
- `items/*/translation.srt`: editable subtitle projection.

Machine translations are explicitly marked `MACHINE`. This capability does not synthesize a voice, clone a voice, burn subtitles into video, mix audio or upload media. Those are downstream MVPs.
