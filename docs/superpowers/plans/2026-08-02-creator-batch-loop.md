# Creator Batch Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an independent, resumable, strictly serial Creator Manifest localization loop and expose it as one browser-managed Video Graph Studio workflow.

**Architecture:** `apps/creator-batch` owns only batch continuation and calls Source Intake, Transcription, Translation, Voice Rendering, and Localization through their public PowerShell launchers. Each item has stable child operation IDs and output roots. Studio composes Creator Discovery, Creator Batch, and read-only verification without owning child artifacts.

**Tech Stack:** Python 3.12 standard library, PowerShell launchers, SQLite-backed Video Graph Studio, vanilla HTML/CSS/JavaScript, pytest.

## Global Constraints

- Exactly one creator item may execute at a time; no parallel item mode.
- Same operation ID plus same canonical fingerprint resumes; changed input conflicts before child execution.
- Completed item facts are reused only while their Localization Manifest hashes still match.
- Cookie path/content never appears in batch receipt or manifest.
- One item failure does not prevent later items from being attempted; any incomplete item keeps the batch `FAILED` and suppresses the final manifest.
- Studio persists only path references and non-secret policies.
- Preserve `apps/localization/localizer/subagent_translation.py` untouched and untracked.

---

### Task 1: Creator Manifest and batch policy contracts

**Files:**
- Create: `apps/creator-batch/creator_batch/contracts.py`
- Create: `apps/creator-batch/creator_batch/__init__.py`
- Test: `tests/creator_batch_mvp/test_contracts.py`

**Interfaces:**
- Consumes: Creator Discovery schema version 1 with ordered `items`.
- Produces: `CreatorSource.load(path)`, `BatchPolicy.create(...)`, and stable canonical fingerprints used by the operation.

- [ ] Write failing tests proving malformed order, duplicate IDs, unsupported URL hosts, empty language/voice coverage, invalid source volume, and secret-free representations are rejected.
- [ ] Run `python -m pytest --import-mode=importlib tests/creator_batch_mvp/test_contracts.py -q` and confirm failure because `creator_batch.contracts` is missing.
- [ ] Implement immutable creator/policy contracts with exact `ru-RU`, `en-US`, and `kk-KZ` language support, HTTPS platform validation, and canonical public dictionaries.
- [ ] Re-run the focused tests and keep them green.

### Task 2: Durable serial continuation owner and real child command adapter

**Files:**
- Create: `apps/creator-batch/creator_batch/child_pipeline.py`
- Create: `apps/creator-batch/creator_batch/operation.py`
- Test: `tests/creator_batch_mvp/test_operation.py`
- Test: `tests/creator_batch_mvp/test_child_pipeline.py`

**Interfaces:**
- Consumes: `CreatorSource`, `BatchPolicy`, optional cookie fingerprint, and `ItemProcessor.process(item, item_root, child_prefix, policy, cookies, on_log)`.
- Produces: atomic `creator-batch-receipt.json`, terminal `creator-batch-manifest.json`, and `BatchResult(result_class, receipt_path, manifest_path, error)`.

- [ ] Write a failing operation test with three real creator items and a deterministic external-operation fake proving call order, maximum concurrency one, continue-after-failure, and no aggregate manifest on partial failure.
- [ ] Run the focused test and confirm failure because the operation is missing.
- [ ] Implement atomic checkpoints, stable item roots/IDs, bounded errors, partial continuation, completed-item hash fencing, duplicate completion, and conflict rejection.
- [ ] Add a failing resume test: after one failure, rerun must skip the two hash-verified items and retry only the failed item.
- [ ] Implement resume and stale-output repair, then rerun operation tests.
- [ ] Write a failing child adapter test using executable fixture launchers that emit complete child JSON/manifest facts; assert exact stage order and that each successor consumes the prior committed manifest.
- [ ] Implement `PublicMvpItemProcessor` with argv-only subprocess calls, JSON result validation, stable stage operation IDs, and Localization Manifest hashing.
- [ ] Re-run both focused files.

### Task 3: Independent launcher and capability packaging

**Files:**
- Create: `apps/creator-batch/creator_batch/cli.py`
- Create: `apps/creator-batch/run.ps1`
- Create: `apps/creator-batch/install.ps1`
- Create: `apps/creator-batch/mvp.json`
- Create: `apps/creator-batch/README.md`
- Test: `tests/creator_batch_mvp/test_cli.py`
- Modify: `scripts/test-all.ps1`
- Modify: `tests/repository/test_repository_layout.py`

**Interfaces:**
- Command: `run.ps1 localize <creator-manifest> --target-language <lang> --voice <lang>=<voice> --output-dir <dir> --operation-id <id> [--cookies <path>] --json`.
- Fact: final JSON includes result class, receipt path, optional manifest path, and bounded error only.

- [ ] Write failing CLI tests for successful execution injection, duplicate language/voice rejection, missing cookies, and JSON output redaction.
- [ ] Implement parser, launcher, installer doctor, manifest, and README.
- [ ] Run `apps/creator-batch/install.ps1` and the entire `tests/creator_batch_mvp` suite.
- [ ] Register the 23rd MVP in repository validation and the full-suite launcher.

### Task 4: Compose the batch into Video Graph Studio

**Files:**
- Modify: `apps/video-graph-studio/studio/api.py`
- Modify: `apps/video-graph-studio/studio/adapters.py`
- Modify: `apps/video-graph-studio/studio/server.py`
- Modify: `apps/video-graph-studio/web/index.html`
- Modify: `apps/video-graph-studio/web/app.js`
- Test: `tests/video_graph_studio/test_creator_batch_graph.py`
- Modify: `tests/video_graph_studio/test_web_shell.py`

**Interfaces:**
- Template: `creator-batch-dub` with `discover-creator -> verify-creator -> localize-creator-batch -> verify-creator-batch`.
- Browser payload: creator URL/max items/cookie path, target languages/voices, ASR policy, translation policy, source volume.

- [ ] Write failing API tests proving the four-node graph, same-home cookie admission, no cookie content persistence, and rejection of invalid language/voice policy.
- [ ] Implement Graph admission and parameters.
- [ ] Write failing adapter tests proving the committed Creator Manifest is passed to the independent launcher and the batch verifier checks exact creator item/language coverage plus derivative hashes.
- [ ] Implement and register both adapters.
- [ ] Write failing browser-shell assertions for **Creator+Dub**, its controls, payload, four-node labels, and progress count.
- [ ] Implement the UI mode and rerun all Studio tests.

### Task 5: Evidence, documentation, and delivery

**Files:**
- Create: `docs/mvp/creator-batch/{vertical-slice-brief.md,capability-dag.md,capability-evidence.md,delivery-ledger.md}`
- Create: `docs/project/evidence/creator-batch/delivery-ledger.md`
- Create: `docs/training/13-creator-batch-loop.md`
- Modify: `README.md`, `TOOLS.md`, `apps/README.md`, `docs/WORKFLOWS.md`
- Modify: `docs/project/planning/capability-roadmap.md`, `docs/project/product/creator-automation-studio.md`
- Modify: `docs/project/evidence/README.md`, `docs/project/evidence/video-graph-studio/delivery-ledger.md`
- Modify: `docs/project/architecture/design/blueprints/video-graph-studio.md`

- [ ] Record the owner, DAG, RED evidence, failure matrix, substitutes, supported level, missing platform evidence, and forbidden claims.
- [ ] Update the root workflow diagram, app count, test count after verification, tools table, roadmap, product slice, and training index.
- [ ] Run focused tests, full repository tests/manifests, compileall, Node syntax, PowerShell parse, installer doctor, diff check, and a high-signal secret scan.
- [ ] Stage only slice files, commit intentionally, push, open a PR, merge to `main`, and verify the head commit is an ancestor of `origin/main`.
