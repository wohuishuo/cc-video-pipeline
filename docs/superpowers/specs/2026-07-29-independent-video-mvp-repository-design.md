# Independent Video MVP Repository Design

## Observable result

A new contributor can clone the repository, open the English root README, select one capability, install only that capability, run its CLI, and understand its inputs, outputs, dependencies, failure behavior, tests, and verified delivery level without reading unrelated code.

## Scope

The repository becomes a monorepo of independently runnable applications. Existing working implementations are migrated behind stable application boundaries rather than rewritten for appearance. Concrete video productions remain under `projects/`; generated media, models, caches, process files, and credentials are excluded from Git.

Tracked source code, developer documentation, CLI help, and reusable templates use English. User-authored scripts, subtitles, research data, proper names, and media-project content retain their source language because translation would change content rather than improve the programming interface.

## Applications

| Application | Observable result | State owner |
|---|---|---|
| `platform-io` | Download or prepare an upload for one supported platform and emit a receipt | platform job receipt store |
| `transcription` | Convert one media file into transcript JSON and SRT | transcript output directory |
| `signal-analysis` | Measure shot boundaries and loudness without extracting frames | analysis result directory |
| `frame-extraction` | Extract interval or cut-aligned frames from one video | frame-set directory |
| `video-editing` | Produce a silence-cut or reframed derivative | requested output file |
| `localization` | Compose transcript, translation, voice, subtitles, and timing into a localized derivative | localization manifest |
| `voice-cloning` | Register a voice and synthesize speech using a selected engine | voice registry and output directory |
| `channel-research` | Collect and render channel/video metadata | research workspace |
| `remotion-studio` | List, preview, and render reusable compositions | composition registry; render output belongs to caller |

## Repository structure

```text
apps/<mvp>/
  README.md
  mvp.json
  run.ps1
  install.ps1
  src/ or package source
  tests/
packages/
  contracts/        # receipt and manifest schemas only
projects/           # concrete productions and source material
docs/mvp/<mvp>/     # brief, DAG, evidence, ledger
scripts/            # repository-level doctor and test runners only
```

No application imports another application's private implementation. Composition occurs through versioned files or public CLI contracts. Shared packages may contain schemas and process primitives, but not workflow ownership.

## Application contract

Every `apps/<name>/mvp.json` contains `schema_version`, `name`, `summary`, `entrypoint`, `install`, `test`, `inputs`, `outputs`, `dependencies`, and `delivery_level`. Repository tests reject missing fields, broken relative paths, non-English reusable documentation, and application-to-application private imports.

Every application supports `run.ps1 --help` or an equivalent forwarded help command. Installation is application-local and idempotent. Runtime data is written outside source directories unless an explicit output path is supplied.

## Migration strategy

Use a strangler migration. First install the repository shell and contract validation. Then integrate the completed platform I/O branch. Migrate the lowest-dependency capabilities in this order: signal analysis, frame extraction, transcription, editing, channel research, voice cloning, localization, Remotion Studio. Compatibility wrappers may remain temporarily at old paths and must forward to the new public entrypoint.

## Protected invariants

- Each mutable artifact has exactly one application owner.
- Applications do not silently mutate inputs.
- Credentials and browser profiles never enter Git or receipts.
- A successful command must verify its declared output exists and is readable.
- Generated artifacts are not reusable source code.
- Delivery claims match executable evidence.
- Existing uncommitted user work is preserved.

## Error handling and evidence

CLIs return zero only after verifying outputs. Structured receipts record adapter, command result, media facts where applicable, and redacted errors. Each MVP has focused tests, at least one adjacent integration test, a failure matrix, and the four required MVP artifacts.

## Non-goals

- Splitting the monorepo into separate GitHub repositories.
- Translating user video scripts or subtitles merely for consistency.
- Rewriting proven algorithms when a wrapper provides a clean contract.
- Committing downloaded models, source videos, rendered previews, audio, cookies, or browser profiles.
- Claiming authenticated upload verification without a real draft/private platform test.

## Git integration

Implementation occurs on an isolated branch. The completed `video-platform-io` commits are incorporated there. After clean repository tests, manifest validation, launcher checks, and a clean diff audit, the branch is merged locally into `main`. Existing unrelated working-tree changes remain untouched; if they prevent a safe merge, the verified branch remains ready and the exact blocker is reported rather than stashing or committing user work.
