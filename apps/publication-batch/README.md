# Publication Batch MVP

Consume one verified Localization Manifest and create a private/draft Publication Plan for every localized derivative, one at a time:

```powershell
.\apps\publication-batch\run.ps1 plan C:\Jobs\localization-manifest.json `
  --metadata-template C:\Jobs\metadata.json `
  --target youtube=primary `
  --credential youtube=youtube-main `
  --target tiktok=brand `
  --output-dir C:\Jobs\publication-batch `
  --operation-id release-plan-001 --json
```

The metadata template requires `title` and may include `description` plus a string-array `tags`. These fields support `{media_id}`, `{language}` and `{filename}`. Rendered metadata and child Publication Plans remain editable local files.

Exactly one derivative and one Publication child are active at a time. A failure is checkpointed while later derivatives are still attempted. Repeating the identical operation skips hash-verified completed plans and repairs incomplete or stale items with the same child IDs. Changed input under the same operation ID conflicts.

Credential IDs are non-secret references. This MVP never opens Credential Vault, accepts credential plaintext, contacts a platform or creates public publication intent.
