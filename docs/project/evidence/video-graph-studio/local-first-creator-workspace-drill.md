# Local-First Creator Workspace Drill

Date: 2026-08-03
Environment: Windows 11, real loopback Studio on `127.0.0.1:8765`, in-app browser, existing local media under the user's OneDrive Desktop.

## Purpose

Verify the creator workflow as an understandable local application rather than a decorative graph editor. The drill focuses on the failures reported by the operator: only three restored videos, mandatory uploads, hidden translation policy, missing voice-provider selection and unusable OneDrive folder paths.

## Observed facts

| Boundary | Browser/API observation | Result |
| --- | --- | --- |
| stale partial account catalog | restored catalog displayed `3` items, `complete=false`, `truncated=true`, a truthful warning, **Load all videos** and an explicit partial-processing option | passed |
| authentication recovery | the restored source form repopulated the prior local authentication-file path without loading cookie contents into browser state | passed |
| strict partial admission | the API continued to reject an incomplete catalog when `allowPartialCatalog` was omitted | passed |
| explicit partial admission | selecting all three discovered videos and enabling **Process only the currently loaded videos** produced a ready preflight while retaining the partial-catalog label | passed |
| partial local workload | Russian plus English with Edge TTS projected three source videos, six local MP4 files and zero upload routes; **Start local processing** was enabled | passed |
| full discovery retry | one browser click submitted `maxItems=0` with the restored authentication-file reference; run `5bfa7769-5f94-44b1-b6f1-26fce880bd4e` completed with 75 verified videos | passed |
| local source | `C:\Users\eugen\OneDrive\Desktop` was accepted and projected exactly four supported video files | passed |
| translation | NLLB and DeepSeek appeared as separate large provider choices; 20 locales were visible | passed |
| voice | Edge TTS, Qwen3-TTS and original audio/subtitles appeared as independent choices | passed |
| Qwen3 policy | selecting Qwen3 replaced Edge text inputs with explicit preset selectors for Russian and English | passed |
| local completion | output defaulted to `C:\Users\eugen\Videos`; the publication section remained closed and had zero routes | passed |
| exact review | four local videos and two languages projected eight local MP4 outputs and zero publication jobs | passed |
| admission | preflight said all local-processing conditions were ready and enabled **Start local processing** with no platform selected | passed |
| responsive layout | at 800 × 900, document width equaled viewport client width and no horizontal page overflow appeared | passed |
| console | no browser error entries after reload, partial-catalog preflight and 75-item discovery | passed |

## Safety boundary

The final start button was not clicked because doing so would begin a real multi-video download, ASR, translation, voice synthesis and composition workload. The live read-only Douyin discovery did run to completion. The drill proves browser-to-contract composition, exact catalog enumeration and admission, not completed media quality, elapsed rendering performance or upload execution.

The creator adapter performed platform pagination. No browser session was opened or scrolled on Douyin, and no cookie contents were copied into the browser application. Full catalog manifest SHA-256: `593c0bc777dc991fe7d690c24a8d65680c009ac117798f62a76cca8402d9ce57`.

## Interaction redesign drill

The version-13 workspace shell was exercised again in the in-app browser after the operator-facing redesign. The existing complete creator catalog was retained; no discovery, rendering or publication job was started.

| Interaction | Observation | Result |
| --- | --- | --- |
| stage navigation | each footer action named the next decision: video list, translation, voice, output and final review | passed |
| complete catalog selection | **Select all 75 videos** selected exactly 75 rendered catalog cards | passed |
| multilingual projection | Russian plus English remained visibly selected and projected 150 local derivatives | passed |
| voice and destination | Edge TTS remained explicit; local output was `C:\Users\eugen\Videos`; publication routes remained zero | passed |
| actionable review | review showed source, translation, voice and output as separate editable sections; the translation edit action returned directly to the translation stage | passed |
| launch state | the ready panel explained serial, resumable execution and enabled **Start local processing** | passed |
| desktop containment | at a 1932-pixel browser client width, document scroll width equaled client width | passed |
| browser console | no error entries were recorded during the complete seven-stage drill | passed |

The browser session did not advertise a viewport-resize capability, so the new breakpoints were checked by deterministic shell assertions rather than by claiming another live mobile screenshot. The existing 800 x 900 browser evidence above remains the runtime proof for the same normal-flow workspace structure.
