# MVP Vertical Slices Refactor Design

## Goal

Turn the repository from a mixed collection of scripts, skills, experiments, and video projects into independently runnable and verifiable capability MVPs. Preserve useful behavior while moving composition into thin workflow coordinators.

The first observable result is:

> Given a supported video URL, produce a verifiable set of downloaded media, normalized audio, transcript data, scene-change data, loudness data, and key frames. A failed run can be resumed without corrupting completed outputs.

## Current Problems

- PowerShell entry points contain a previous computer's absolute root path.
- `tools/` mixes shared runtime code, standalone products, experiments, and concrete Remotion videos.
- `.claude/skills/` mixes executable automation with prompt-only content workflows.
- File existence doubles as workflow state, so a partial or stale artifact can be mistaken for a completed capability.
- Python, PowerShell, FFmpeg, Node, and model-specific concerns cross boundaries without stable contracts.
- The coordinator directly knows script locations, runtime locations, output layouts, and retry rules.
- There are few focused contract tests, so successful installation is often confused with verified behavior.

## Chosen Approach

Use capability-oriented MVPs with a thin coordinator.

Each MVP must have:

- one observable result;
- one public command-line entry point;
- an explicit input/output contract;
- exactly one owner for each mutable state;
- focused tests that do not require the entire pipeline;
- optional platform adapters behind the public contract;
- a machine-readable result or artifact manifest.

An MVP does not need to be published as an installable package. Independence means it can be invoked and verified without running unrelated capabilities.

### Rejected alternatives

1. **Stage-oriented P0/P1/P2 folders.** This is a small initial change, but each stage would still combine unrelated state owners and runtimes.
2. **Clean-room rewrite.** This would produce a tidy structure but discard proven FFmpeg, yt-dlp, transcription, and TTS behavior.

## Target Capability Boundaries

| Capability | Observable result | State owned |
| --- | --- | --- |
| `workspace-core` | Resolve a portable workspace and allocate artifact locations | workspace configuration and artifact catalog |
| `media-fetch` | Turn a URL into validated media and normalized audio | acquisition record and media metadata |
| `transcription` | Turn audio into the canonical transcript schema | transcript and transcription run metadata |
| `signal-analysis` | Produce scene-change and loudness data | signal-analysis result |
| `frame-extraction` | Produce a bounded key-frame set and manifest | frame-set result |
| `reference-analysis` | Resume and compose reference-analysis steps | job lifecycle and continuation state only |
| `content-authoring` | Produce versioned brief, titles, script, and storyboard | authored document versions |
| `tts` | Turn approved text into audio with declared engine settings | synthesis run and voice configuration reference |
| `visual-rendering` | Render a declared visual composition | render job and render output metadata |
| `video-editing` | Produce edited horizontal and vertical exports | edit/export job state |
| `bilibili-insights` | Produce source and publishing insight read models | collected snapshots and derived projections |
| `video-pipeline` | Compose verified capabilities into a project workflow | top-level project continuation state only |

Existing Claude skills remain user-facing guidance. They call capability entry points but do not become state owners.

## Vertical Slice Brief: Reference Analysis

### Observable result

One command accepts a video URL and job slug and returns a manifest containing validated paths and metadata for media, audio, transcript, scene cuts, loudness samples, and frames.

### Use cases

- `create-reference-job`
- `fetch-media`
- `transcribe-audio`
- `analyze-signals`
- `extract-frames`
- `resume-reference-job`
- `show-reference-result`

### State owners and invariants

| State | Unique owner | Protected invariant | Public mutation | Public read/fact |
| --- | --- | --- | --- | --- |
| workspace root and artifact catalog | `workspace-core` | all paths are inside the selected workspace; slugs cannot escape it | allocate artifact set | artifact paths allocated |
| acquisition record and media metadata | `media-fetch` | published media passed duration and stream validation | fetch media | media acquired |
| transcript and engine metadata | `transcription` | SRT and JSON describe the same run and source audio | transcribe audio | transcript committed |
| cuts and loudness result | `signal-analysis` | results identify the source media and analysis parameters | analyze signals | signals committed |
| frame set and manifest | `frame-extraction` | frame count respects limits and every manifest entry exists | extract frames | frames committed |
| job lifecycle and continuation | `reference-analysis` | a step is complete only after its owner commits a result | run or resume job | job advanced / job failed |

### Protected invariants

- Authority: only the owning capability marks its result committed.
- Ownership: the coordinator cannot write another capability's result metadata.
- Idempotency: repeating a completed command returns the committed result or creates a new explicit run; it does not silently mix outputs.
- Versioning: manifests record schema version, source identity, relevant parameters, and engine/tool identity.
- Lifecycle: temporary output is not treated as committed output.
- Recovery: a failed step leaves prior committed facts valid and exposes a resumable failure.

### Decision gates

- `DECISION_REQUIRED`: whether later project-level outputs use the same artifact manifest format as reference analysis. This does not block the first slice.
- `DECISION_REQUIRED`: whether content documents eventually use filesystem-only versions or Git-backed versions. This does not block the first slice.

### Non-goals

- No GUI.
- No database or service framework.
- No cloud queue.
- No model download during ordinary contract tests.
- No rewrite of every existing script in the first slice.
- No production-scale or platform-completeness claim.

## Capability DAG

Arrows mean that the predecessor provides a proven contract or committed fact consumed by the successor.

```text
workspace-core
  --Adapter(substitute: fake filesystem)--> media-fetch
media-fetch
  --Fact: MediaAcquired---------------> transcription
  --Fact: MediaAcquired---------------> signal-analysis
  --Fact: MediaAcquired---------------> frame-extraction
workspace-core
  --Factory: ArtifactSet--------------> reference-analysis
media-fetch
  --Fact: MediaAcquired---------------> reference-analysis
transcription
  --Fact: TranscriptCommitted---------> reference-analysis
signal-analysis
  --Fact: SignalsCommitted------------> reference-analysis
frame-extraction
  --Fact: FramesCommitted-------------> reference-analysis
```

| Node | Owner | Initial status | Direct dependencies | Dependency class |
| --- | --- | --- | --- | --- |
| `workspace-core` | workspace owner | unproven | fixed workspace specification; fake filesystem adapter | substitute |
| `media-fetch` | acquisition owner | implemented but unverified behind a contract | `workspace-core`; yt-dlp/FFmpeg adapters | hard owner contract; substitutable platform adapters |
| `transcription` | transcript owner | implemented but unverified behind a contract | committed media/audio fact; engine strategy | hard source fact; substitutable engine |
| `signal-analysis` | signal owner | implemented but unverified behind a contract | committed media fact; FFmpeg adapter | hard source fact; substitutable adapter |
| `frame-extraction` | frame-set owner | implemented but unverified behind a contract | committed media fact; optional cuts query; FFmpeg adapter | hard source fact; cuts are optional strategy input |
| `reference-analysis` | job coordinator | implemented as a coupled script | all committed facts above | hard facts |

The lowest unproven node is `workspace-core`. The hard-coded old-computer root path prevents portable independent invocation of every downstream capability.

## Contract Shape

Every capability command returns a JSON-compatible result envelope:

```json
{
  "schema_version": "1",
  "capability": "media-fetch",
  "run_id": "stable-or-generated-id",
  "status": "committed",
  "inputs": {},
  "outputs": {},
  "tool_versions": {},
  "warnings": []
}
```

Failed runs return a non-zero exit code and a result with `status: failed` when a safe result location exists. Temporary files are written below a run-specific temporary directory and promoted only after validation.

## Migration Strategy

1. Add contracts, manifests, and tests before moving large amounts of code.
2. Implement `workspace-core` without changing legacy entry points.
3. Wrap existing behavior behind one capability at a time.
4. Keep compatibility shims at existing script paths.
5. Prove each capability with fake adapters, focused tests, and one adjacent integration using the previous real capability.
6. Replace `p0_pipeline.ps1` internals with the thin `reference-analysis` coordinator only after its dependencies are verified.
7. Apply the same pattern to TTS, editing, rendering, authoring, and insights.
8. Move concrete video compositions and experimental code only after their capability owner is clear.

## Capability Evidence Requirements

For every MVP record:

- public contract and unique owner;
- a failing RED assertion before implementation;
- focused contract tests;
- adjacent integration using the previous real capability;
- duplicate, conflict, stale, reentry, partial-failure, and cleanup behavior;
- exact commands and results;
- explicit non-goals.

Platform-heavy adapters use small generated fixtures in normal tests. Network downloads and large model execution are separate platform-integration checks.

## Test Strategy

### Contract tests

- workspace discovery from repository root and nested directories;
- explicit `--workspace` override;
- slug traversal rejection;
- deterministic artifact allocation;
- result envelope schema validation;
- idempotent rerun and stale-result detection.

### Adapter tests

- fake yt-dlp, FFmpeg, and transcription engines record arguments and create bounded fixtures;
- adapter failures preserve prior committed results;
- partial outputs remain uncommitted and are cleanable.

### Adjacent integrations

- real `workspace-core` with fake `media-fetch` adapter;
- real `media-fetch` contract with generated local media and real FFmpeg;
- real transcription contract with a fake engine before any large-model check;
- real signal/frame capabilities with a short generated video fixture;
- full reference coordinator with network and model substitutes;
- optional platform checks for a real URL and locally installed model.

## Repository Layout Direction

```text
capabilities/
  workspace-core/
  media-fetch/
  transcription/
  signal-analysis/
  frame-extraction/
  reference-analysis/
  content-authoring/
  tts/
  visual-rendering/
  video-editing/
  bilibili-insights/
  video-pipeline/
contracts/
tests/
projects/
.claude/skills/
```

The first implementation creates only the directories needed by the first proven node. Empty future capability scaffolds are not created.

## Delivery Ledger

- Supported completion level: `DESIGNED`.
- Evidence present: repository inventory, current workflow inspection, state-owner matrix, typed dependency graph, migration order, test strategy.
- Evidence missing: RED tests, implemented contracts, focused test results, adjacent integration results, real platform checks.
- Substitutes planned: fake filesystem, fake downloader, fake FFmpeg, fake transcription engine, generated media fixtures.
- Decisions unapproved: shared project/reference manifest policy; long-term content-document version policy.
- Forbidden claims: independently runnable MVPs exist; the reference pipeline is domain verified; network downloading is platform integrated; model transcription is production verified; the whole video pipeline is production ready.

