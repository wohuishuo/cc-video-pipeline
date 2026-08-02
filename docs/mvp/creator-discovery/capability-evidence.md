# Creator Discovery capability evidence

- Contract tests cover supported HTTPS hosts, limits and credential-free public projection.
- Operation tests cover serial pagination, checkpointing, deterministic deduplication, truncation, replay, conflict and failure resume.
- Adapter tests cover flat yt-dlp metadata, canonical YouTube URLs and optional cookie forwarding without logging.
- A pinned-F2 compatibility doctor prevents silent upstream import drift.

Real platform run `douyin-profile-live-1` on 2026-08-02 enumerated the supplied Douyin share profile to three newest canonical video URLs in 8.9 seconds. It identified creator `百年工业`, marked the manifest truncated, preserved the next cursor, stored no cookie material and replayed as `DUPLICATE_COMPLETED` in 510 ms. Manifest SHA-256: `438f4e329ff1b34a1372071a040dafc7739102e44fc5295d4c6817bcc4fa9a6a`.

Full-profile scale, deleted/private item behavior, rate limits and live YouTube/Bilibili/TikTok profile evidence remain missing.
