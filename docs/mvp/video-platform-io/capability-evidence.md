# Capability evidence

| Platform | Download evidence | Upload evidence | Current status |
|---|---|---|---|
| YouTube | Anonymous real download, 1920×1080, audio present, 213.054 s | Repository-owned private API route is domain-tested; no account draft test | download production-verified; upload domain-verified |
| Bilibili | Anonymous real download, 1280×720, audio present, 127.384 s; 1080 CDN attempts truncated | Adapter installed; no account draft test | download production-verified at 720p; upload implemented |
| Douyin | yt-dlp requested fresh cookies; f2 returned empty API responses and no media | Adapter installed; no account draft test | implemented, externally blocked without usable session/cookie |
| TikTok | yt-dlp extractor failed on two real URLs; f2 TikTok initialization failed to obtain msToken | Bridge installed; no account draft test | implemented, externally blocked without usable session/token |

Automated evidence covers platform routing, credential redaction and the non-empty external-ID gate. The product rejects a zero exit code when no media file or declared upload identity exists, so failed third-party extraction or incomplete publication cannot be reported as success.

Receipts are written under the chosen output directory as `download-receipt.json`. Cookie contents and cookie paths are redacted from persisted receipts.
