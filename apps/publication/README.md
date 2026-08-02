# Guarded Publication MVP

Guarded Publication separates intent from execution. Planning never contacts a platform:

```powershell
.\apps\publication\run.ps1 plan C:\Videos\final.mp4 `
  --metadata C:\Videos\metadata.json `
  --target youtube=primary `
  --credential youtube=youtube-main `
  --target tiktok=brand `
  --output-dir C:\Jobs\publish-plan `
  --operation-id plan-001 --json
```

Execution requires the exact SHA-256 of `publication-plan.json`:

```powershell
.\apps\publication\run.ps1 execute C:\Jobs\publish-plan\publication-plan.json `
  --confirmation <PLAN_SHA256> `
  --credential-vault "$env:LOCALAPPDATA\VideoGraphStudio\credential-vault.json" `
  --output-dir C:\Jobs\publish-run `
  --operation-id publish-001 --json
```

`--credential platform=credential-id` stores a non-secret reference in that target job. During execution, the adapter asks Credential Vault to verify that the stored provider matches the platform, then injects the value into only the Platform I/O child as `VIDEO_PLATFORM_CREDENTIAL`. No secret or plaintext hash enters the plan, receipt, manifest or argv.

Plans are private/draft by default. At present, only YouTube's pinned adapter can force private visibility; guarded execution rejects private/draft Bilibili, Douyin and TikTok jobs. Creating a public plan requires `--public`, and execution still requires the exact plan hash. Credential-aware process composition has local domain evidence; no authenticated upload has real-platform evidence yet.

Each platform executes serially and checkpoints independently. A retry never repeats a completed job whose fingerprints still match.
