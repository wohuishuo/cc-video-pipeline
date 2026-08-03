# Video Graph Studio capability evidence

The focused suite proves graph validation, verified creator catalog projection, immutable Creator Selection lineage, selected Campaign admission, 20-locale contract drift prevention, selectable NLLB/DeepSeek adapter policy, in-workspace DeepSeek credential setup, per-language destination validation, exact workload counts, durable queue/recovery, subprocess fencing and browser shell boundaries.

DeepSeek setup stores the key through Credential Vault's Windows CurrentUser DPAPI boundary. Studio exposes only provider readiness, and Credential Vault injects the plaintext into the one Translation or Creator Batch child environment. Focused tests prove the secret is absent from argv and API responses; a real temporary-vault drill proves the persisted JSON contains no plaintext.

Live browser evidence covers a real three-item Douyin account catalog, select-all, Russian and English voices, Russian-to-YouTube/TikTok plus English-to-YouTube routing, exact `3 source / 6 localized / 9 publication` counts, an actionable DeepSeek setup card with selectable provider state, zero console errors and zero document overflow at desktop and mobile width.

On 2026-08-03, the completion projection was exercised against the real completed run `93cd7dcc-e848-46b3-b297-4d2b06a34a31`. The projector revalidated its Creator Batch, Localization, Translation and MP4 fingerprints, reported `217.866s` of media and `53.4 MB`, and the browser loaded the byte-range media endpoint to `readyState 4` with no media error. The source run predates provider usage capture, so the UI correctly displayed token usage as not reported. The same UI had no horizontal overflow at an `820px` viewport. Chinese, English and Russian display selection and persistence were browser verified.

Measured voice evidence:

| Adapter | Policy | Evidence |
| --- | --- | --- |
| Qwen3-TTS | One resident model, eight independent clips per generation call | A real 129-segment run completed in `285.18s`, down from `1352.38s`, with exact segment coverage. |
| Edge TTS | Six bounded network requests | Twelve clips / `44.76s` of audio took `52.188s` at one worker, `17.219s` at three, `9.203s` at six and `9.125s` at eight. Six is the measured plateau policy. |

The Studio Python suite contains `141` passing tests, and the adjacent browser models contain `21` passing Node tests at this checkpoint.

Run:

```powershell
tools\.venv\Scripts\python.exe -m pytest tests/video_graph_studio -q
node --test tests/video_graph_studio/*.test.mjs
```

See [creator-workspace-drill.md](../../project/evidence/video-graph-studio/creator-workspace-drill.md).
