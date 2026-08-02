# Creator Selection

Creator Selection is an independent, local capability MVP. It accepts a Creator Discovery manifest plus one or more video IDs and commits an immutable, ordered subset for downstream download and localization. It never downloads media and never modifies the source manifest.

```powershell
.\apps\creator-selection\run.ps1 select C:\path\creator-manifest.json `
  --video-id VIDEO_A --video-id VIDEO_B `
  --output-dir C:\path\selection --operation-id selection-001 --json
```

Selection order is derived from the source manifest, so the same ID set produces the same fact even if the caller submits IDs in another order. Unknown IDs, duplicates, and empty selections are rejected. Replaying the same operation is safe; changing its inputs returns `REJECTED_CONFLICT`.
