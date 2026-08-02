# Creator Discovery MVP

Creator Discovery converts one YouTube, Bilibili, Douyin or TikTok creator URL into an ordered, deduplicated `creator-manifest.json`. It does not download videos.

Delivery level: `PLATFORM_INTEGRATED`. A bounded real Douyin profile enumeration and credential-free receipt replay are verified; the other supported adapters remain domain-tested only.

```powershell
.\apps\creator-discovery\run.ps1 profile "https://www.youtube.com/@creator/videos" `
  --max-items 20 `
  --output-dir "C:\Jobs\creator" `
  --operation-id creator-001 `
  --json
```

For Douyin, add `--cookies C:\path\cookies.txt` when anonymous enumeration is rejected. The cookie path and content are never stored in the manifest or receipt.

Pages are processed one at a time and checkpointed. Repeating an identical completed operation returns `DUPLICATE_COMPLETED`; repeating an interrupted/failed operation continues from its committed cursor when the adapter supports it. `max-items 0` requests every available item.

## Boundary

This MVP owns discovery only. Platform I/O downloads or uploads; Source Intake owns media files; Graph Studio may command these owners but does not merge their state.
