# Source Intake MVP

Source Intake converts either a local folder or one supported social-video URL into a deterministic `source-manifest.json` and an idempotent `intake-receipt.json`.

```powershell
.\apps\source-intake\run.ps1 folder "C:\Videos" --output-dir "C:\Jobs\intake" --operation-id job-1 --json
.\apps\source-intake\run.ps1 url "https://youtu.be/..." --output-dir "C:\Jobs\intake" --operation-id job-2 --json
```

YouTube, Bilibili, Douyin and TikTok URLs are supported through the independent Platform I/O MVP. Anonymous download is attempted first; cookies are optional with `--cookies cookies.txt`. Cookie paths and contents are never written to Source Intake receipts.

One operation runs at a time. Repeating the same operation ID and input returns the original verified result; changing the input conflicts instead of overwriting it.

