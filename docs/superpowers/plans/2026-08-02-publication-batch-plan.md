# Publication Batch Planning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do not dispatch subagents; the user explicitly prohibited them.

**Goal:** Add a reusable strict-serial Publication Batch planner and compose it after folder/URL multilingual localization in Video Graph Studio.

**Architecture:** The new MVP consumes a committed Localization Manifest, renders deterministic metadata for each derivative, and invokes the existing Publication public launcher once per derivative with stable child operation IDs. It owns only batch checkpoints and the aggregate plan; Studio consumes the committed Localization fact and projects the independent batch result through two additional Graph nodes.

**Tech Stack:** Python 3.12 standard library, PowerShell launchers, existing Video Graph Studio Python/HTML/CSS/JavaScript, pytest, FFprobe artifact facts already committed by Localization.

## Global Constraints

- Process exactly one derivative and one child Publication command at a time.
- Preserve Localization derivative order and target order.
- Accept only private/draft planning; do not contact any platform.
- Persist credential IDs only; never accept or persist credential plaintext.
- Same operation ID and fingerprint resumes; changed input under the same operation ID conflicts.
- Continue after an item failure, but do not emit an aggregate plan until every item is verified complete.
- Do not modify or stage `apps/localization/localizer/subagent_translation.py`.

---

### Task 1: Publication Batch input contracts and metadata rendering

**Files:**
- Create: `tests/publication_batch_mvp/test_contracts.py`
- Create: `apps/publication-batch/publication_batch/__init__.py`
- Create: `apps/publication-batch/publication_batch/contracts.py`

**Interfaces:**
- Consumes: `localization-manifest.json`, metadata-template JSON, platform/account mappings and optional platform/credential-ID mappings.
- Produces: `LocalizationInput`, `Derivative`, `MetadataTemplate`, `BatchPolicy`, `load_localization_manifest(path)`, `load_metadata_template(path)`, `render_metadata(template, derivative)` and `sha256_file(path)`.

- [ ] **Step 1: Write failing contract tests**

```python
def test_loader_preserves_derivative_order_and_verifies_files(tmp_path):
    manifest = write_localization_manifest(tmp_path, [("ru-RU", "m1"), ("en-US", "m1")])
    value = load_localization_manifest(manifest)
    assert [(row.target_language, row.media_id) for row in value.derivatives] == [("ru-RU", "m1"), ("en-US", "m1")]

def test_metadata_renderer_expands_only_supported_tokens(tmp_path):
    template = load_metadata_template(write_template(tmp_path, "{filename} · {language} · {media_id}"))
    rendered = render_metadata(template, derivative(tmp_path, language="ru-RU", media_id="m1"))
    assert rendered["title"] == "localized · ru-RU · m1"

def test_changed_or_duplicate_derivative_and_unknown_token_are_rejected(tmp_path):
    with pytest.raises(BatchContractError):
        load_localization_manifest(write_duplicate_manifest(tmp_path))
    with pytest.raises(BatchContractError, match="unsupported metadata token"):
        load_metadata_template(write_template(tmp_path, "{unknown}"))
```

- [ ] **Step 2: Run tests and observe RED**

Run: `python -m pytest --import-mode=importlib tests/publication_batch_mvp/test_contracts.py -q`

Expected: collection fails because `publication_batch` does not exist.

- [ ] **Step 3: Implement strict contracts**

```python
@dataclass(frozen=True)
class Derivative:
    ordinal: int
    target_language: str
    media_id: str
    path: Path
    sha256: str
    size: int

@dataclass(frozen=True)
class BatchPolicy:
    targets: Sequence[tuple[str, str]]
    credentials: Sequence[tuple[str, str]]

def render_metadata(template: MetadataTemplate, derivative: Derivative) -> dict[str, object]:
    replacements = {"{media_id}": derivative.media_id, "{language}": derivative.target_language, "{filename}": derivative.path.stem}
    return template.render(replacements)
```

Require schema version 1, exact derivative coverage/order, unique `(targetLanguage, mediaId)`, supported target platforms, bounded identifiers, real file size/hash, a non-empty title and no brace token outside the three approved tokens.

- [ ] **Step 4: Run contract tests and observe GREEN**

Run: `python -m pytest --import-mode=importlib tests/publication_batch_mvp/test_contracts.py -q`

Expected: all contract tests pass.

### Task 2: Durable strict-serial planning operation

**Files:**
- Create: `tests/publication_batch_mvp/test_operation.py`
- Create: `apps/publication-batch/publication_batch/operation.py`

**Interfaces:**
- Consumes: validated `LocalizationInput`, `MetadataTemplate`, `BatchPolicy`, output directory, operation ID and a `PlanItemProcessor` adapter.
- Produces: `PublicationBatchOperation.execute(localization, template, policy, output_dir, operation_id, processor, on_log=None) -> BatchResult`, `publication-batch-receipt.json`, rendered item metadata and `publication-batch-plan.json`.

- [ ] **Step 1: Write the first failing operation tests**

```python
def test_operation_plans_every_derivative_strictly_in_manifest_order(tmp_path):
    processor = RecordingProcessor()
    result = PublicationBatchOperation().execute(inputs(), template(), policy(), tmp_path / "out", "batch-1", processor)
    assert result.result_class == "COMPLETED"
    assert processor.maximum_active == 1
    assert processor.calls == [("ru-RU", "m1"), ("en-US", "m1")]

def test_failed_item_is_checkpointed_later_items_continue_and_retry_is_stable(tmp_path):
    first = RecordingProcessor(fail={"m1:ru-RU"})
    failed = execute(first)
    assert failed.result_class == "FAILED"
    assert failed.manifest_path is None
    retry = RecordingProcessor()
    completed = execute(retry)
    assert retry.calls == [("ru-RU", "m1")]
    assert completed.result_class == "COMPLETED"
```

- [ ] **Step 2: Run operation tests and observe RED**

Run: `python -m pytest --import-mode=importlib tests/publication_batch_mvp/test_operation.py -q`

Expected: import or missing-operation failure.

- [ ] **Step 3: Implement atomic receipt and aggregate state**

```python
class PublicationBatchOperation:
    def execute(self, localization, template, policy, output_dir, operation_id, processor, on_log=None) -> BatchResult:
        state = self._load_or_initialize(localization, template, policy, output_dir, operation_id)
        for derivative in localization.derivatives:
            state = self._reuse_or_plan(state, derivative, template, policy, processor, on_log)
            self._commit_receipt(state)
        return self._commit_aggregate_if_complete(state)
```

Use stable item roots `items/{ordinal:04d}-{sha256[:12]}`, child IDs `{operation_id}:plan:{ordinal}:{language}:{media_id}:{derivative_sha[:12]}`, same-directory atomic JSON replacement, and a receipt item for every attempted derivative. A reused item must verify derivative hash, metadata hash, child plan hash and child plan coverage.

- [ ] **Step 4: Add duplicate/conflict/stale/secret tests**

```python
def test_completed_replay_does_not_call_processor(tmp_path):
    execute(RecordingProcessor())
    replay = RecordingProcessor()
    assert execute(replay).result_class == "DUPLICATE_COMPLETED"
    assert replay.calls == []

def test_same_operation_id_with_changed_targets_conflicts_without_mutation(tmp_path):
    execute(RecordingProcessor(), targets={"youtube": "main"})
    receipt_before = receipt_path.read_bytes()
    assert execute(RecordingProcessor(), targets={"tiktok": "brand"}).result_class == "REJECTED_CONFLICT"
    assert receipt_path.read_bytes() == receipt_before

def test_stale_plan_or_metadata_is_repaired_with_same_child_identity(tmp_path):
    execute(RecordingProcessor())
    child_plan.write_text("changed", encoding="utf-8")
    repair = RecordingProcessor()
    assert execute(repair).result_class == "COMPLETED"
    assert repair.child_ids == [original_child_id]

def test_receipt_and_manifest_exclude_credential_values_and_vault_paths(tmp_path):
    result = execute(RecordingProcessor(), credentials={"youtube": "youtube-main"})
    persisted = result.receipt_path.read_text(encoding="utf-8") + result.manifest_path.read_text(encoding="utf-8")
    assert "youtube-main" in persisted
    assert "credentialValue" not in persisted and "credentialVault" not in persisted
```

- [ ] **Step 5: Run operation suite and observe GREEN**

Run: `python -m pytest --import-mode=importlib tests/publication_batch_mvp/test_operation.py -q`

Expected: all operation tests pass with maximum active items one.

### Task 3: Real Publication child adapter and public CLI

**Files:**
- Create: `tests/publication_batch_mvp/test_child_planner.py`
- Create: `tests/publication_batch_mvp/test_cli.py`
- Create: `apps/publication-batch/publication_batch/child_planner.py`
- Create: `apps/publication-batch/publication_batch/cli.py`
- Create: `apps/publication-batch/run.ps1`
- Create: `apps/publication-batch/install.ps1`
- Create: `apps/publication-batch/mvp.json`
- Create: `apps/publication-batch/README.md`

**Interfaces:**
- Consumes: rendered metadata, derivative file, target/account and credential-ID maps.
- Produces: `PublicPublicationPlanner.plan(item, output_dir, operation_id, policy, on_log) -> ChildPlanFact`, CLI `plan` and `doctor` JSON responses.

- [ ] **Step 1: Write failing child and CLI tests**

```python
def test_child_planner_calls_public_publication_launcher_and_verifies_receipt(tmp_path):
    fact = PublicPublicationPlanner(launcher, runner=recording_runner).plan(item, output, "child-id", policy, log)
    assert fact.plan_sha256 == digest(fact.plan_path)
    assert fact.job_count == 2

def test_cli_plan_returns_machine_readable_result(tmp_path):
    code = main(["plan", str(manifest), "--metadata-template", str(metadata), "--target", "youtube=main", "--output-dir", str(output), "--operation-id", "op", "--json"], processor_factory=factory)
    assert code == 0
```

- [ ] **Step 2: Run child/CLI tests and observe RED**

Run: `python -m pytest --import-mode=importlib tests/publication_batch_mvp/test_child_planner.py tests/publication_batch_mvp/test_cli.py -q`

Expected: missing modules and launcher behavior.

- [ ] **Step 3: Implement argv-only child composition and CLI**

Build a PowerShell argv array for `apps/publication/run.ps1 plan`; never use shell string interpolation. Parse only the final JSON line, then independently verify the Planning Receipt, Publication Plan hash, video hash, metadata hash, target order, private/draft visibility and credential-ID coverage.

- [ ] **Step 4: Implement portable launchers, doctor and manifest**

`run.ps1` resolves the repository/common Git tools venv just like existing MVP launchers, sets only `PYTHONPATH` and `PYTHONUTF8`, and invokes `python -m publication_batch.cli`. `install.ps1` runs `doctor --json`. `mvp.json` declares public inputs/outputs and `DOMAIN_VERIFIED`.

- [ ] **Step 5: Run the focused MVP and adjacent real-owner tests**

Run: `python -m pytest --import-mode=importlib tests/publication_batch_mvp -q`

Expected: all tests pass, including one real `PublicationPlanner` adjacent integration rather than two fake owners.

### Task 4: Compose Folder/URL Release Graphs in Studio

**Files:**
- Create: `tests/video_graph_studio/test_publication_batch_graph.py`
- Modify: `apps/video-graph-studio/studio/api.py`
- Modify: `apps/video-graph-studio/studio/adapters.py`
- Modify: `apps/video-graph-studio/studio/server.py`

**Interfaces:**
- Consumes: the committed `localize` node fact from the existing ten-step localization Graph.
- Produces: graph IDs `folder-release` and `url-release`, adapter `PublicationBatchPlanAdapter`, verifier `VerifyPublicationBatchPlanAdapter` and two committed batch facts.

- [ ] **Step 1: Write failing graph/admission tests**

```python
def test_folder_release_graph_has_twelve_owner_steps_and_platform_policy(tmp_path):
    status, response = app.handle("POST", "/api/v1/runs", {}, envelope(release_payload(tmp_path)))
    assert status == 201
    assert [row["id"] for row in response["value"]["graph"]["nodes"]][-2:] == ["plan-publication-batch", "verify-publication-batch"]
```

Also reject missing metadata path, zero targets, unknown platforms, missing account names, credential references without a matching target and any `public: true` field.

- [ ] **Step 2: Run Studio graph tests and observe RED**

Run: `python -m pytest --import-mode=importlib tests/video_graph_studio/test_publication_batch_graph.py -q`

Expected: unknown template or missing adapter failure.

- [ ] **Step 3: Add Graph definitions and strict request admission**

Construct both Graphs from the existing localization node sequence plus the two Publication Batch nodes. Persist metadata-template path, ordered target platforms, one account per platform and bounded credential IDs in run parameters.

- [ ] **Step 4: Add command and verification adapters**

The command adapter locates and hash-verifies the committed Localization Manifest, invokes `apps/publication-batch/run.ps1 plan`, and returns its aggregate path/hash/counts. The verifier independently validates exact derivative order, exact platform coverage, each rendered metadata file/hash, each child plan/hash, private/draft visibility and total job count.

- [ ] **Step 5: Register adapters and run Studio tests**

Run: `python -m pytest --import-mode=importlib tests/video_graph_studio/test_publication_batch_graph.py tests/video_graph_studio/test_localization_graph.py -q`

Expected: Release Graph tests and existing localization tests pass.

### Task 5: Browser Release workflow

**Files:**
- Modify: `apps/video-graph-studio/web/index.html`
- Modify: `apps/video-graph-studio/web/app.js`
- Modify: `apps/video-graph-studio/web/styles.css`
- Modify: `tests/video_graph_studio/test_web_shell.py`

**Interfaces:**
- Consumes: existing source/language/voice controls plus Release-only metadata path, platform/account and credential-ID controls.
- Produces: selectable Folder + Release and URL + Release workflows, twelve-step progress, graph/palette/inspector copy and API payloads.

- [ ] **Step 1: Write failing browser-shell behavior assertions**

Assert both template IDs, Release controls, payload keys, twelve-step projection and new versioned asset names are present. Assert switching away hides Release-only controls.

- [ ] **Step 2: Run browser-shell tests and observe RED**

Run: `python -m pytest --import-mode=importlib tests/video_graph_studio/test_web_shell.py -q`

Expected: missing Release templates/controls.

- [ ] **Step 3: Implement Release workflow UI and payload mapping**

Reuse existing localization controls. Show metadata, account, target platform and optional YouTube credential ID controls only for Release. Update node copy and progress to `0 / 12`. Do not expose public visibility or automatic execution.

- [ ] **Step 4: Run browser-shell and complete Studio suites**

Run: `python -m pytest --import-mode=importlib tests/video_graph_studio -q`

Expected: all Studio tests pass.

### Task 6: Architecture, training and delivery evidence

**Files:**
- Create: `docs/mvp/publication-batch/vertical-slice-brief.md`
- Create: `docs/mvp/publication-batch/capability-dag.md`
- Create: `docs/mvp/publication-batch/capability-evidence.md`
- Create: `docs/mvp/publication-batch/delivery-ledger.md`
- Create: `docs/project/evidence/publication-batch/delivery-ledger.md`
- Create: `docs/training/14-publication-batch-planning.md`
- Modify: `README.md`
- Modify: `TOOLS.md`
- Modify: `apps/README.md`
- Modify: `apps/video-graph-studio/README.md`
- Modify: `docs/PROJECT_MAP.md`
- Modify: `docs/WORKFLOWS.md`
- Modify: `docs/project/architecture/design/blueprints/video-graph-studio.md`
- Modify: `docs/project/evidence/README.md`
- Modify: `docs/project/evidence/video-graph-studio/delivery-ledger.md`
- Modify: `docs/project/planning/capability-roadmap.md`
- Modify: `docs/project/product/creator-automation-studio.md`
- Modify: `scripts/test-all.ps1`
- Modify: `tests/repository/test_repository_layout.py`

**Interfaces:**
- Produces: all four required MVP workflow artifacts, repository navigation, training command, honest evidence level and full-suite registration.

- [ ] **Step 1: Register the 24th independent MVP in repository tests and full suite**

Add `tests/publication_batch_mvp` to `scripts/test-all.ps1` and `publication-batch` to the repository layout expectation.

- [ ] **Step 2: Write capability and architecture documents**

Record owner matrix, typed DAG edges, RED observations, focused/adjacent commands, duplicate/conflict/stale/reentry/partial-failure coverage, substitutes, missing live evidence, decision gates and forbidden upload claims.

- [ ] **Step 3: Write the user tutorial and update navigation**

Document CLI and browser workflows, metadata tokens, resume behavior, inspection paths and the boundary between planning and upload. Update the app count and diagrams without claiming platform execution.

- [ ] **Step 4: Run documentation and repository tests**

Run: `python -m pytest --import-mode=importlib tests/repository tests/publication_batch_mvp tests/video_graph_studio -q`

Expected: all selected suites pass and all documentation links resolve through repository checks.

### Task 7: Real browser/API composition smoke and final verification

**Files:**
- Create after the run: `docs/project/evidence/video-graph-studio/publication-batch-graph-drill.md`
- Modify after the run: `docs/project/evidence/README.md`
- Modify after the run: `docs/project/evidence/video-graph-studio/delivery-ledger.md`

**Interfaces:**
- Produces: one dated loopback evidence record with run ID, exact graph nodes, admitted parameters, browser layout measurements and explicit no-platform-contact boundary.

- [ ] **Step 1: Start Studio with an isolated ignored data root and inspect the browser**

Select Folder + Release and URL + Release, verify source/language/voice/metadata/platform controls, twelve owner steps, visible start button and no console errors.

- [ ] **Step 2: Create one real Release run through loopback HTTP without starting it**

Record the returned run ID, `CREATED` status, exact graph ID, ordered nodes, languages and platforms. Do not contact a remote platform.

- [ ] **Step 3: Record the bounded evidence and stop the server**

Write the drill with explicit supported and forbidden claims; remove the ignored smoke data after verifying its resolved path.

- [ ] **Step 4: Run fresh full verification**

Run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\test-all.ps1
python -m compileall -q apps\publication-batch\publication_batch apps\video-graph-studio\studio tests\publication_batch_mvp tests\video_graph_studio
node --check apps\video-graph-studio\web\app.js
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\apps\publication-batch\install.ps1
git diff --check
```

Expected: every command exits zero, all 24 MVP manifests are valid, doctor reports `maximumActiveItems: 1`, and the full test count is updated in README from the fresh result.

- [ ] **Step 5: Commit, push, create PR and merge to main**

Stage only this slice and leave `apps/localization/localizer/subagent_translation.py` untracked. Use commit `feat: add publication batch planning graph`, push `codex/publication-batch-plan`, create a ready PR to `main`, merge only after GitHub reports it mergeable, fetch `origin/main`, and verify every slice commit is its ancestor.
