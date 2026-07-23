# Information Gap Shot 01 and 38-Shot Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the independent-shot architecture for all 38 planned shots and deliver Shot 01 with reconstructed evidence, licensed investigative music, original transition effects, a still, and a short preview.

**Architecture:** A JSON shot catalog is the authoritative timeline. Remotion registers only implemented shot components plus a development master. Assets and audio are admitted through machine-validated registries. Shot 01 proves the complete contract before later chapter plans implement shots 02–38.

**Tech Stack:** React 19, Remotion 4, TypeScript, Node.js built-in test runner, JSON registries, FFmpeg 8, PowerShell 5.1+, licensed MP3/WAV assets.

## Global Constraints

- Horizontal output only: 1920x1080, 30 fps.
- Existing `informationGap.tsx` is a reference and must not be imported by the new shot system.
- Each shot must render independently and own its composition, assets, sound assignment, and verification receipt.
- The master owns sequencing only.
- Reconstructed interfaces use invented identities and carry `示意重构` where confusion is possible.
- No real phone number, active QR code, unsupported identifiable business, or secret may enter an approved render.
- External audio and B-roll require source page, creator, license URL, download date, attribution, and SHA-256.
- Shot 01 cannot be accepted with placeholder audio or missing licence evidence.
- Preserve unrelated modifications in `docs/mvp/research/capability-evidence.md` and `docs/mvp/research/delivery-ledger.md`.

---

## File Structure

```text
tools/remotion-hello/
  public/information-gap/
    audio/music/
    audio/sfx/
  scripts/
    validate-shot-catalog.mjs
    validate-media-registry.mjs
  src/information-gap-shots/
    catalog.json
    types.ts
    root.tsx
    Master.tsx
    shared/
      palette.ts
      Paper.tsx
      Caption.tsx
      Camera.tsx
      ReconstructionBadge.tsx
    shots/shot-01/
      Shot01.tsx
      shot.json
  test/
    shot-catalog.test.mjs
    media-registry.test.mjs
projects/information-gap-business/
  assets/asset-license.json
  audio/audio-license.json
  audio/cue-sheet.json
  verification/shot-01.json
  previews/shot-01.png
  previews/shot-01.mp4
```

## Task 1: Authoritative 38-Shot Catalog

**Files:**
- Create: `tools/remotion-hello/src/information-gap-shots/catalog.json`
- Create: `tools/remotion-hello/scripts/validate-shot-catalog.mjs`
- Create: `tools/remotion-hello/test/shot-catalog.test.mjs`
- Modify: `tools/remotion-hello/package.json`

**Interfaces:**
- Consumes: the 38 rows in `docs/superpowers/specs/2026-07-23-information-gap-38-shot-remotion-design.md`.
- Produces: `catalog.json` with `{id, chapter, start, end, title, visualResult, materialIds, musicCue, implemented}` for each shot; `validateCatalog(catalog)`.

- [ ] **Step 1: Write the failing catalog contract test**

```javascript
// tools/remotion-hello/test/shot-catalog.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {validateCatalog} from "../scripts/validate-shot-catalog.mjs";

test("catalog defines 38 contiguous independent shots covering 1800 seconds", async () => {
  const path = new URL("../src/information-gap-shots/catalog.json", import.meta.url);
  const catalog = JSON.parse(await readFile(path, "utf8"));
  const result = validateCatalog(catalog);
  assert.deepEqual(result.errors, []);
  assert.equal(result.shotCount, 38);
  assert.equal(result.durationSeconds, 1800);
  assert.equal(new Set(catalog.map((shot) => shot.visualResult)).size, 38);
});
```

- [ ] **Step 2: Run RED**

Run:

```powershell
cd tools\remotion-hello
node --test test\shot-catalog.test.mjs
```

Expected: failure because `validate-shot-catalog.mjs` and `catalog.json` do not exist.

- [ ] **Step 3: Implement the validator**

```javascript
// tools/remotion-hello/scripts/validate-shot-catalog.mjs
export const validateCatalog = (catalog) => {
  const errors = [];
  if (!Array.isArray(catalog)) return {errors: ["catalog must be an array"], shotCount: 0, durationSeconds: 0};
  if (catalog.length !== 38) errors.push(`expected 38 shots, got ${catalog.length}`);
  let cursor = 0;
  const ids = new Set();
  const visualResults = new Set();
  for (const [index, shot] of catalog.entries()) {
    const expectedId = `shot-${String(index + 1).padStart(2, "0")}`;
    if (shot.id !== expectedId) errors.push(`${expectedId}: id mismatch`);
    if (ids.has(shot.id)) errors.push(`${shot.id}: duplicate id`);
    ids.add(shot.id);
    if (shot.start !== cursor) errors.push(`${shot.id}: expected start ${cursor}, got ${shot.start}`);
    if (!(shot.end > shot.start)) errors.push(`${shot.id}: end must be greater than start`);
    cursor = shot.end;
    for (const key of ["chapter", "title", "visualResult", "musicCue"]) {
      if (typeof shot[key] !== "string" || !shot[key].trim()) errors.push(`${shot.id}: missing ${key}`);
    }
    if (!Array.isArray(shot.materialIds) || shot.materialIds.length < 2) errors.push(`${shot.id}: at least two material IDs required`);
    if (visualResults.has(shot.visualResult)) errors.push(`${shot.id}: visualResult duplicates a prior shot`);
    visualResults.add(shot.visualResult);
  }
  if (cursor !== 1800) errors.push(`catalog must end at 1800, got ${cursor}`);
  return {errors, shotCount: catalog.length, durationSeconds: cursor};
};
```

- [ ] **Step 4: Create all 38 catalog records**

Translate every design-table row exactly. Convert times to seconds and set only `shot-01` to `"implemented": true`; set shots 02–38 to `false`. Use material IDs from R01–R06, C01–C06, O01–O03, B01–B05, and explicit original IDs such as `ORIGINAL-CASHFLOW-QUESTION`. Every `visualResult` must be the full unique visual-result sentence from the specification.

- [ ] **Step 5: Add test scripts and run GREEN**

Add to `package.json`:

```json
"test:shots": "node --test test/*.test.mjs",
"validate:shots": "node scripts/validate-shot-catalog.mjs"
```

Run:

```powershell
node --test test\shot-catalog.test.mjs
```

Expected: 1 test passed, 0 failed; 38 shots and 1800 seconds.

- [ ] **Step 6: Commit**

```powershell
git add tools/remotion-hello/src/information-gap-shots/catalog.json tools/remotion-hello/scripts/validate-shot-catalog.mjs tools/remotion-hello/test/shot-catalog.test.mjs tools/remotion-hello/package.json
git commit -m "feat(remotion): define authoritative 38-shot catalog"
```

## Task 2: Licensed Media Registries

**Files:**
- Create: `projects/information-gap-business/assets/asset-license.json`
- Create: `projects/information-gap-business/audio/audio-license.json`
- Create: `projects/information-gap-business/audio/cue-sheet.json`
- Create: `tools/remotion-hello/scripts/validate-media-registry.mjs`
- Create: `tools/remotion-hello/test/media-registry.test.mjs`

**Interfaces:**
- Consumes: local media files and provenance data.
- Produces: `validateMediaRegistry({assets, audio, cues, root})` with blocking errors.

- [ ] **Step 1: Write a failing registry test**

```javascript
// tools/remotion-hello/test/media-registry.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import {validateMediaRegistry} from "../scripts/validate-media-registry.mjs";

test("approved media requires provenance, license and digest", () => {
  const result = validateMediaRegistry({
    assets: [{id: "R01", kind: "reconstruction", creator: "cc-video-pipeline", license: "original", file: "r01.png", sha256: "a".repeat(64)}],
    audio: [{id: "M01", kind: "music", creator: "AtlasAudio", sourcePage: "https://pixabay.com/music/ambient-tension-documentary-519912/", licenseUrl: "https://pixabay.com/service/license-summary/", downloadedAt: "2026-07-23", file: "tension-documentary.mp3", sha256: "b".repeat(64)}],
    cues: [{id: "M01", shots: ["shot-01"], gainDb: -23, fadeInFrames: 18, fadeOutFrames: 24, duckDb: -8}],
    checkFiles: false,
  });
  assert.deepEqual(result.errors, []);
});

test("noncommercial audio is rejected", () => {
  const result = validateMediaRegistry({audio: [{id: "bad", licenseUrl: "CC-BY-NC"}], assets: [], cues: [], checkFiles: false});
  assert.ok(result.errors.some((error) => error.includes("noncommercial")));
});
```

- [ ] **Step 2: Run RED**

Run `node --test test\media-registry.test.mjs`.

Expected: module-not-found failure for the registry validator.

- [ ] **Step 3: Implement registry validation**

Implement checks for unique IDs, required creator/source/license/download date/file/SHA fields, 64-character lowercase SHA-256, forbidden `NC` licences, cue shot IDs, gain range `-40..0`, non-negative fades, and file existence when `checkFiles` is true. Return `{errors: string[]}` and never silently downgrade an error.

- [ ] **Step 4: Acquire Shot 01 music and create original effects**

Download `Tension Documentary` by AtlasAudio from its official Pixabay item page into:

```text
tools/remotion-hello/public/information-gap/audio/music/m01-tension-documentary.mp3
```

Record the official item page and Pixabay licence page in `audio-license.json`. Calculate SHA-256 with:

```powershell
Get-FileHash -Algorithm SHA256 tools\remotion-hello\public\information-gap\audio\music\m01-tension-documentary.mp3
```

Generate four original paper impacts and one low bass hit with FFmpeg noise/sine sources; save WAV files below `public/information-gap/audio/sfx/` and register creator as `cc-video-pipeline`, licence `original`.

- [ ] **Step 5: Run GREEN and commit**

Run:

```powershell
node --test test\media-registry.test.mjs
node scripts\validate-media-registry.mjs
```

Expected: registry tests pass and local-file validation reports zero errors.

```powershell
git add projects/information-gap-business/assets projects/information-gap-business/audio tools/remotion-hello/public/information-gap/audio tools/remotion-hello/scripts/validate-media-registry.mjs tools/remotion-hello/test/media-registry.test.mjs
git commit -m "feat(remotion): add licensed audio and media registry"
```

## Task 3: Independent Composition Root and Shared Primitives

**Files:**
- Create: `tools/remotion-hello/src/information-gap-shots/types.ts`
- Create: `tools/remotion-hello/src/information-gap-shots/root.tsx`
- Create: `tools/remotion-hello/src/information-gap-shots/Master.tsx`
- Create: `tools/remotion-hello/src/information-gap-shots/shared/palette.ts`
- Create: `tools/remotion-hello/src/information-gap-shots/shared/Paper.tsx`
- Create: `tools/remotion-hello/src/information-gap-shots/shared/Caption.tsx`
- Create: `tools/remotion-hello/src/information-gap-shots/shared/Camera.tsx`
- Create: `tools/remotion-hello/src/information-gap-shots/shared/ReconstructionBadge.tsx`
- Modify: `tools/remotion-hello/src/root.tsx`

**Interfaces:**
- Consumes: implemented shot component map and catalog timing.
- Produces: Remotion compositions `ig-shot-01` and `information-gap-shots-dev`.

- [ ] **Step 1: Add a failing composition discovery check**

Run before implementation:

```powershell
npx.cmd remotion compositions src/root.tsx | Select-String "ig-shot-01"
```

Expected: no match and non-success assertion in the execution receipt.

- [ ] **Step 2: Define types**

```typescript
export type ShotCatalogItem = {
  id: string;
  chapter: string;
  start: number;
  end: number;
  title: string;
  visualResult: string;
  materialIds: string[];
  musicCue: string;
  implemented: boolean;
};

export type ShotProps = {shot: ShotCatalogItem};
```

- [ ] **Step 3: Implement shared primitives**

Implement only low-level visual atoms:

- `Paper`: textured paper surface with configurable rotation, tone and shadow.
- `Caption`: one or two lines in the lower safe area.
- `Camera`: frame-driven scale and translate wrapper.
- `ReconstructionBadge`: visible `示意重构` label.
- `palette.ts`: ink, charcoal, ivory, blue, red, amber and muted text constants.

None may contain shot-specific layout or content.

- [ ] **Step 4: Implement composition registration**

`root.tsx` imports the catalog, registers `ig-shot-01` at `(end-start)*30` frames, and registers a development master containing implemented shots only. Append `<InformationGapShotsRoot />` to the existing root without removing legacy compositions.

- [ ] **Step 5: Run composition discovery and commit**

Run:

```powershell
npx.cmd remotion compositions src/root.tsx
```

Expected: existing compositions plus `ig-shot-01` and `information-gap-shots-dev`.

Commit with `feat(remotion): add independent shot composition root`.

## Task 4: Shot 01 Premium Evidence Desk

**Files:**
- Create: `tools/remotion-hello/src/information-gap-shots/shots/shot-01/shot.json`
- Create: `tools/remotion-hello/src/information-gap-shots/shots/shot-01/Shot01.tsx`
- Create: `projects/information-gap-business/verification/shot-01.json`

**Interfaces:**
- Consumes: catalog `shot-01`, R01–R04 reconstructions, M01, four paper hits, one bass hit.
- Produces: an eight-second independently renderable investigation-desk shot.

- [ ] **Step 1: Write the shot contract before implementation**

`shot.json` must declare:

```json
{
  "id": "shot-01",
  "purpose": "Introduce four low-price/high-promise entry offers and ask the governing question.",
  "requiredVisualObjects": ["R01", "R02", "R03", "R04", "QUESTION", "PRESENTER_PIP"],
  "caption": "你刷到过这种东西吗？",
  "musicCue": "M01",
  "soundEffects": ["PAPER-01", "PAPER-02", "PAPER-03", "PAPER-04", "BASS-QUESTION"],
  "forbidden": ["active QR", "real phone", "real company", "unsupported earnings claim"]
}
```

- [ ] **Step 2: Render RED**

Run:

```powershell
npx.cmd remotion still src/root.tsx ig-shot-01 ..\..\projects\information-gap-business\previews\shot-01.png --frame=135
```

Expected: failure because `Shot01.tsx` is absent or unregistered.

- [ ] **Step 3: Implement the complete Shot 01 component**

The component must contain four visually different reconstructed interfaces:

- dark AI-course browser page with `9.9` price;
- ivory egg-event registration form with inactive geometric QR;
- warm franchise brochure with equipment-cost reverse side;
- blue phone recruitment page with chat preview.

Place them on a textured evidence desk at four different angles and depths. Animate each with separate spring timing, add string/arrow connections, show a presenter PIP silhouette only as a small anchor, then push the camera toward the vertical question at frames 150–225. Use `<Audio>` for M01 and the five effects with cue-sheet gains. Add the caption and reconstruction badges.

- [ ] **Step 4: Render still and preview**

```powershell
npx.cmd remotion still src/root.tsx ig-shot-01 ..\..\projects\information-gap-business\previews\shot-01.png --frame=135
npx.cmd remotion render src/root.tsx ig-shot-01 ..\..\projects\information-gap-business\previews\shot-01.mp4 --frames=0-239 --codec=h264
```

Expected: 1920x1080 still and eight-second H.264 preview with audible music/effects.

- [ ] **Step 5: Verify and record receipt**

Record exact render commands, file SHA-256, dimensions, duration, catalog version, asset/audio IDs, licence validation result, forbidden-content scan, and visual inspection result in `verification/shot-01.json`. Status may become `accepted` only after all fields pass.

- [ ] **Step 6: Commit**

Commit with `feat(remotion): deliver independently verified shot 01`.

## Task 5: Foundation Evidence and Next-Batch Gate

**Files:**
- Create: `docs/mvp/information-gap-shots/vertical-slice-brief.md`
- Create: `docs/mvp/information-gap-shots/capability-dag.md`
- Create: `docs/mvp/information-gap-shots/capability-evidence.md`
- Create: `docs/mvp/information-gap-shots/delivery-ledger.md`

- [ ] **Step 1: Run full foundation verification**

```powershell
cd tools\remotion-hello
npm.cmd run test:shots
npx.cmd remotion compositions src/root.tsx
node scripts\validate-media-registry.mjs
ffprobe -v error -show_entries stream=width,height -show_entries format=duration -of json ..\..\projects\information-gap-business\previews\shot-01.mp4
git diff --check
```

Expected: tests pass, Shot 01 compositions exist, registries have zero errors, preview is 1920x1080 and approximately 8 seconds.

- [ ] **Step 2: Write the four workflow artifacts**

Set delivery level to `PLATFORM_INTEGRATED` only for Shot 01 if real Remotion rendering, FFmpeg probing, licensed audio, registry validation, and visual inspection all pass. Explicitly state that shots 02–38 and the final master remain unimplemented.

- [ ] **Step 3: Commit evidence**

Commit with `docs(remotion): record shot 01 platform evidence`.

- [ ] **Step 4: Continue without user architecture questions**

Create the next implementation plan for shots 02–05 using the same contract. Each later chapter plan must contain exact shot-specific layouts, media IDs, audio cues, still frames, preview ranges, and acceptance commands. Do not batch-accept a chapter from one render.

