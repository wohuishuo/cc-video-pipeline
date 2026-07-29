# Capability evidence

| Platform | Download evidence | Upload evidence | Current status |
|---|---|---|---|
| YouTube | Anonymous real download, 1920×1080, audio present, 213.054 s | Adapter installed; no account draft test | download production-verified; upload implemented |
| Bilibili | Anonymous real download, 1280×720, audio present, 127.384 s; 1080 CDN attempts truncated | Adapter installed; no account draft test | download production-verified at 720p; upload implemented |
| Douyin | yt-dlp requested fresh cookies; f2 returned empty API responses and no media | Adapter installed; no account draft test | implemented, externally blocked without usable session/cookie |
| TikTok | yt-dlp extractor failed on two real URLs; f2 TikTok initialization failed to obtain msToken | Bridge installed; no account draft test | implemented, externally blocked without usable session/token |

Automated evidence: `python -m pytest tests/video_platform -q` passes 32 tests. The product rejects a zero exit code when no media file exists, so failed third-party extraction cannot be reported as success.

Receipts are written under the chosen output directory as `download-receipt.json`. Cookie contents and cookie paths are redacted from persisted receipts.
