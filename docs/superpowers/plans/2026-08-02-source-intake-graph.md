# Source Intake Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Execute inline and sequentially; do not use subagents.

**Goal:** Add an independently runnable Source Intake MVP that turns a local folder or supported social URL into a durable standard media manifest, then expose it as a Video Graph Studio source template.

**Architecture:** Source Intake owns operation fencing and the standard source manifest. Folder discovery is a local strategy. URL transport invokes the existing Platform I/O public launcher through a replaceable process adapter and consumes its redacted receipt. Graph Studio owns only continuation and projection.

**Tech Stack:** Python 3.12 standard library, PowerShell 5.1, SQLite-backed Graph Studio, pytest, existing `platform-io` CLI.

## Global Constraints

- No parallel downloads or source jobs.
- Never persist cookie paths, contents, tokens or browser profiles.
- Same operation ID and canonical input replays; changed input conflicts.
- Publish manifest and receipt atomically only after verifying referenced media.
- Invoke Platform I/O through `apps/platform-io/run.ps1`; do not import its private implementation.
- Keep folder and URL intake reusable without Graph Studio.

---

### Task 1: Source specification and deterministic folder discovery

**Files:**
- Create: `apps/source-intake/intake/contracts.py`
- Create: `apps/source-intake/intake/folder.py`
- Create: `apps/source-intake/intake/__init__.py`
- Test: `tests/source_intake/test_folder.py`

**Interfaces:**
- Produces: `SourceSpec.folder(path)`, `SourceSpec.url(value)`, `classify_url(value)`, `discover_folder(spec) -> SourceManifest`.
- Consumes: resolved folder paths and supported HTTPS URLs.

- [ ] Write a failing test that discovers supported media recursively in deterministic order and rejects an empty folder.
- [ ] Run `python -m pytest tests/source_intake/test_folder.py -q` and observe missing-module RED.
- [ ] Implement immutable schema-v1 contracts, host classification and deterministic discovery.
- [ ] Add traversal, unsupported-host and non-video tests; run focused tests.
- [ ] Commit with `feat(source-intake): discover deterministic folder manifests`.

### Task 2: Idempotent operation owner and atomic receipts

**Files:**
- Create: `apps/source-intake/intake/operation.py`
- Test: `tests/source_intake/test_operation.py`

**Interfaces:**
- Produces: `IntakeOperation.execute(spec, output_dir, operation_id, transport=None) -> IntakeResult`.
- Consumes: `SourceSpec`, folder discovery or a URL transport port.

- [ ] Write a failing same-operation replay test asserting the original manifest is returned.
- [ ] Observe RED because the operation owner is missing.
- [ ] Implement canonical fingerprinting, conflict fencing, atomic manifest/receipt publication and reference revalidation.
- [ ] Add changed-input conflict, missing-output replay and failed-transport tests.
- [ ] Run focused tests and commit with `feat(source-intake): own idempotent intake receipts`.

### Task 3: Platform I/O adapter and public application

**Files:**
- Create: `apps/source-intake/intake/platform_adapter.py`
- Create: `apps/source-intake/intake/cli.py`
- Create: `apps/source-intake/run.ps1`
- Create: `apps/source-intake/install.ps1`
- Create: `apps/source-intake/mvp.json`
- Create: `apps/source-intake/README.md`
- Test: `tests/source_intake/test_platform_adapter.py`
- Test: `tests/source_intake/test_public_app.py`

**Interfaces:**
- Adapter: `PlatformIOTransport.fetch(spec, output_dir, on_log) -> TransportResult`.
- CLI: `folder|url SOURCE --output-dir DIR --operation-id ID [--cookies FILE] [--max-height 1080] --json`.

- [ ] Write a failing adapter test using a real short-lived fake public launcher that writes a Platform I/O receipt and media.
- [ ] Observe missing adapter RED.
- [ ] Implement argv-only PowerShell invocation, output streaming and receipt/media verification.
- [ ] Add failure/redaction/CLI contract tests and public application files.
- [ ] Run Source Intake plus repository manifest tests and commit with `feat(source-intake): add public folder and URL intake MVP`.

### Task 4: Graph and browser composition

**Files:**
- Modify: `apps/video-graph-studio/studio/adapters.py`
- Modify: `apps/video-graph-studio/studio/api.py`
- Modify: `apps/video-graph-studio/studio/server.py`
- Modify: `apps/video-graph-studio/web/index.html`
- Modify: `apps/video-graph-studio/web/app.js`
- Modify: `apps/video-graph-studio/web/styles.css`
- Test: `tests/video_graph_studio/test_intake_graph.py`
- Update: `docs/project/evidence/video-graph-studio/*`
- Create: `docs/mvp/source-intake/{vertical-slice-brief,capability-dag,capability-evidence,delivery-ledger}.md`

**Interfaces:**
- `POST /api/v1/runs` accepts `templateId` equal to `prepared-localization`, `folder-intake` or `url-intake`.
- Graph adapter invokes Source Intake using stable child operation ID and returns manifest/receipt paths.

- [ ] Write failing API tests for folder and URL template admission and graph topology.
- [ ] Observe RED because templates are not supported.
- [ ] Implement template catalog, Source Intake adapter and prior-step fact context.
- [ ] Update browser Folder/URL source selector and dynamic graph labels without enabling unverified platform publication.
- [ ] Run focused and adjacent suites, start the real server, verify folder intake through the browser/API, update honest evidence and commit.

## Self-review

- All design requirements map to a task.
- Public signatures are consistent across tasks.
- Every production behavior begins with a RED assertion.
- Transcription, translation, dubbing and upload remain later independent plans.
- No placeholders or subagent execution are present.

