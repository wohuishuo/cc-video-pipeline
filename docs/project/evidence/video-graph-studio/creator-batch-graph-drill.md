# Creator Batch Graph Composition Drill

Date: 2026-08-02

## Purpose

Verify that the browser and loopback API expose the Creator Manifest to sequential localization workflow as one composed Graph without claiming a live multi-video localization run.

## Environment

- Local Video Graph Studio server on `127.0.0.1:8877`
- Isolated ignored data root: `tmp/creator-batch-smoke`
- Browser workflow: `Creator + Dub`
- Target languages: `ru-RU`, `en-US`

## Observations

The browser selected graph `creator-batch-dub`, displayed all required creator, authentication-reference, language, ASR, translation and voice controls, and projected the four owner steps:

1. `discover-creator`
2. `verify-creator`
3. `localize-creator-batch`
4. `verify-creator-batch`

The real loopback create endpoint accepted run `e806b8b2-fa0c-4012-9495-03949a8340f6` with status `CREATED`, the exact four-node graph and languages `ru-RU,en-US`. The browser console contained no errors.

At the final layout check, the Creator + Dub control bar had equal `clientHeight` and `scrollHeight` of 179 pixels; the start button was inside the visible bounds and the control bar had no hidden vertical overflow.

## Evidence boundary

This drill proves browser/API composition, admission and presentation only. The run was deliberately not started and no remote platform was contacted. The independently executable domain tests prove strict-serial item continuation and derivative validation; a live multi-item Creator + Dub run remains missing before promotion beyond `DOMAIN_VERIFIED`.
