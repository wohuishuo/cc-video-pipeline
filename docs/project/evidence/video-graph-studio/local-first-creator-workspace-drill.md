# Local-First Creator Workspace Drill

Date: 2026-08-03
Environment: Windows 11, real loopback Studio on `127.0.0.1:8765`, in-app browser, existing local media under the user's OneDrive Desktop.

## Purpose

Verify the creator workflow as an understandable local application rather than a decorative graph editor. The drill focuses on the failures reported by the operator: only three restored videos, mandatory uploads, hidden translation policy, missing voice-provider selection and unusable OneDrive folder paths.

## Observed facts

| Boundary | Browser/API observation | Result |
| --- | --- | --- |
| stale partial account catalog | restored catalog displayed `3` items, `complete=false`, `truncated=true`, a blocking warning and **Load all videos** actions | passed |
| local source | `C:\Users\eugen\OneDrive\Desktop` was accepted and projected exactly four supported video files | passed |
| translation | NLLB and DeepSeek appeared as separate large provider choices; 20 locales were visible | passed |
| voice | Edge TTS, Qwen3-TTS and original audio/subtitles appeared as independent choices | passed |
| Qwen3 policy | selecting Qwen3 replaced Edge text inputs with explicit preset selectors for Russian and English | passed |
| local completion | output defaulted to `C:\Users\eugen\Videos`; the publication section remained closed and had zero routes | passed |
| exact review | four local videos and two languages projected eight local MP4 outputs and zero publication jobs | passed |
| admission | preflight said all local-processing conditions were ready and enabled **Start local processing** with no platform selected | passed |
| responsive layout | at 800 × 900, document width equaled viewport client width and no horizontal page overflow appeared | passed |
| console | no browser error entries after reload and source-mode interaction | passed |

## Safety boundary

The final start button was not clicked because doing so would begin a real multi-video ASR, translation, Qwen3 synthesis and composition workload. This drill proves browser-to-contract composition and admission, not completed media quality, elapsed performance or upload execution.
