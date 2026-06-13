## Bug Fixes (2026-06-12)

via `/code-review` xhigh → 6 bugs found + 8 repaired

| # | File | Line (was) | What | Fix |
|---|---|---|---|---|
| 1 | `silence_cut.ps1` | 82 | concat filter label `[v]` (same for all segments) when concat expects `[v0][v1][v2]` — filter graph broken | Each segment gets unique label `[v0o][v1o]...[vNo]`, loop-indexed |
| 2 | `to_vertical.ps1` | 48 | Windows drive-letter colon (`C:\...`) in `subtitles='path':force_style=...` — ffmpeg filtergraph parser sees `C` as filename, rest as options | `$Subtitle.Replace('\','/')` + `subtitles=filename='...'` |
| 3 | `bilibili_data.py` | 103 | `get_danmakus(page_index=1)` when bilibili_api 17.x expects **0‑based** → skips P1 | `page = 0` instead of `1` |
| 4 | `fetch.ps1` | 63 | `--js-runtimes` appended to `$cookiesArgs` — fragile: if no cookie, js‑runtimes is the only arg before URL | Separate `$runtimeArgs` array, concatenated only at end |
| 5 | `silence_cut.ps1` | 90 | `-c copy` cutting when gaps between keyframes can be 1‑10s → not frame-exact | Primary path: `filter_complex` + re-encode (frame-accurate); concat‑demuxer is fallback only |
| 6 | `probe.ps1` | 17 | `pts_time` captured from frame AFTER scene change → cuts.txt ~1 frame late | Subtract 0.04s from each cut time (≈1/25th of a second) |

**Bonus repairs**
- `bilibili_data.py:43` — `open(cookie_file)` → `open(cookie_file, encoding="utf-8")`
- `silence_cut.ps1:86‑95` — `Out-File -Encoding ascii -Append` which writes a UTF-8 BOM on first call → `Set-Content -Encoding ascii` (no BOM) + `Add-Content` for subsequent lines
- `remotion-hello/package.json:6` — build script updated to point at `src/root.tsx hello-world`
- `probe.ps1:28` — `file=$Dir\rms.txt` is relative-to-CWD parsed by ffmpeg ametadata, file landed in shell CWD instead of `$Dir` → use `Join-Path (Resolve-Path $Dir) "rms.txt"` (absolute path)
