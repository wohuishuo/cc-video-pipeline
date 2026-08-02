# Guided Graph UI Live Drill

Date: 2026-08-02  
Environment: Windows, loopback `http://127.0.0.1:8765/`  
Branch: `codex/studio-guided-graph-ui`

## Purpose

Verify that Video Graph Studio behaves as a truthful guided Graph builder rather than a decorative ComfyUI imitation. The drill used the public `run.ps1` launcher and the real in-app browser.

## Startup boundary

- Found 16 inactive Python processes belonging to eight stale Studio launcher pairs across ports 8765–8769; every reported `activeWorkers: 0`.
- Stopped only those verified `python -m studio.server` processes.
- Started one current launcher process on `127.0.0.1:8765`.
- Verified exactly one listener, Client Contract version `1.0`, 19 catalog workflows, zero queued runs and zero active workers.
- The launcher regression test starts from a directory containing a hostile same-named `studio` package. The current launcher still returns the current contracts and all 19 workflows.

## Browser interaction evidence

| Check | Observed result |
|---|---|
| Initial workflow | `url-dub` |
| Exact graph projection | 10 nodes, 9 Fact edges |
| Loop projection | Source, Transcription, Translation, Voice, Localization (5 unique Loops) |
| Preflight | Contract, health, workspace and catalog independently ready; missing URL independently blocked mutation |
| Zoom in | Label `100% -> 110%`; `--graph-zoom: 1.1` |
| Fit | Label `110% -> 60%`; `--graph-zoom: 0.6` |
| Node inspection | Step 07 selected `Render translated voice`; Inspector showed `Voice` Loop |
| Reconnect | System returned `System ready`, input draft and completed run remained selected |
| Layout | 1932 × 1272 viewport; document, body and client width all 1932; no page-level horizontal overflow |

## Safe run evidence

A generated one-second local MP4 was placed in `tmp/studio-guided-ui-source`. The UI selected **Prepare source media → Folder** and admitted a local-only Graph.

- Run ID: `d6a42fa9-aa13-40da-a6f0-3579a5effab3`
- Graph: `folder-intake`
- Ordered nodes: `intake`, `verify-source`
- Result: `COMPLETED`
- Progress: `2 / 2`
- Verified source coverage: one media file
- Platform contact: none

## Honest boundary

This drill is live loopback/browser evidence for catalog discovery, guided composition, controls and local execution. It does not prove mobile layout, authenticated YouTube upload, Bilibili/Douyin/TikTok publication, remote hosting, representative load, power-loss recovery or production operations.
