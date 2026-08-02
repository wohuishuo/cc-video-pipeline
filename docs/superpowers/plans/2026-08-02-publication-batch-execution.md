# Publication Batch Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute every eligible child plan in a confirmed Publication Batch Plan strictly serially, resumably and through existing public owners, then expose that capability as a separately confirmed Studio Graph.

**Architecture:** First preserve credential-scoped identity and uncertain outcomes across YouTube Publisher → Platform I/O → Publication. Then add an independent Publication Batch Execution continuation owner that validates the entire batch before side effects, calls Publication through its public launcher once per derivative and commits only its own aggregate fact. Video Graph Studio resolves a committed Release planning run and projects a separate two-node execution Graph.

**Tech Stack:** Python 3.11+, PowerShell launchers, JSON file contracts, SQLite-backed Video Graph Studio, vanilla HTML/CSS/JavaScript, pytest.

## Global Constraints

- At most one Publication child or external upload may be active at a time.
- The exact Publication Batch Plan SHA-256 is mandatory confirmation.
- Current executable policy is credential-backed `youtube` with `private-or-draft` visibility only.
- Credential values stay inside Credential Vault and one child environment; only bounded Credential IDs may persist.
- `UNKNOWN` is a durable quarantine fact and must never be retried automatically.
- Bilibili, Douyin and TikTok are rejected before the first side effect.
- Publication Batch Execution owns only batch continuation and aggregate execution evidence.
- `apps/localization/localizer/subagent_translation.py` is unrelated user work and must never be staged.

---

### Task 1: Preserve upload identity and uncertain outcomes

**Files:**
- Modify: `video_platform/cli.py`
- Modify: `apps/publication/publication/execution.py`
- Modify: `apps/publication/publication/cli.py`
- Test: `tests/video_platform/test_cli.py`
- Test: `tests/publication_mvp/test_execution.py`

**Interfaces:**
- Consumes: YouTube Publisher JSON `{resultClass,value:{externalId,detail}}`.
- Produces: Platform I/O `--execution-scope youtube-main` and JSON `childResultClass`; `ExecutionOutcome(completed, external_id, facts, error=None, result_class=None)`; Publication `UNKNOWN`/`REJECTED_UNKNOWN` receipts and exit code `3`.

- [ ] **Step 1: Write failing upload-scope and outcome-fidelity tests**

```python
def test_credential_execution_scope_changes_youtube_child_identity(tmp_path):
    assert _upload_digest(video, metadata, "primary", "youtube-a") != _upload_digest(video, metadata, "primary", "youtube-b")

def test_internal_youtube_unknown_is_preserved(capsys, monkeypatch):
    # fake child returns resultClass UNKNOWN and exit 3
    assert payload["childResultClass"] == "UNKNOWN"
```

- [ ] **Step 2: Run the focused tests and observe RED**

Run: `C:\Users\eugen\OneDrive\Documents\video\tools\.venv\Scripts\python.exe -m pytest --import-mode=importlib tests/video_platform/test_cli.py tests/publication_mvp/test_execution.py -q`

Expected: failure because `_upload_digest` has no execution scope and Publication flattens unknown outcomes.

- [ ] **Step 3: Implement bounded scope and lossless result mapping**

```python
def _upload_digest(video, metadata, account=None, execution_scope=None):
    digest = hashlib.sha256()
    for path in (video.resolve(), metadata.resolve()):
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
    if account is not None:
        digest.update(account.encode("utf-8"))
    if execution_scope is not None:
        digest.update(b"\0scope\0" + execution_scope.encode("utf-8"))
    return digest.hexdigest()

@dataclass(frozen=True)
class ExecutionOutcome:
    completed: bool
    external_id: str | None
    facts: dict[str, Any]
    error: str | None = None
    result_class: str | None = None
```

Platform I/O must emit the child's exact `resultClass` without echoing stdout/stderr. Publication passes `credentialId` as `--execution-scope`, checkpoints `UNKNOWN`, returns `UNKNOWN` on first uncertainty and returns `REJECTED_UNKNOWN` without calling the adapter when replay sees an unknown receipt.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the command from Step 2. Expected: all selected tests pass.

- [ ] **Step 5: Commit the enabling hardening**

```powershell
git add video_platform/cli.py apps/publication/publication/execution.py apps/publication/publication/cli.py tests/video_platform/test_cli.py tests/publication_mvp/test_execution.py
git commit -m "fix: preserve publication upload outcomes"
```

### Task 2: Define strict Publication Batch Execution contracts

**Files:**
- Create: `apps/publication-batch-execution/publication_batch_execution/__init__.py`
- Create: `apps/publication-batch-execution/publication_batch_execution/contracts.py`
- Test: `tests/publication_batch_execution_mvp/test_contracts.py`

**Interfaces:**
- Consumes: `load_batch_plan(path, confirmation)` and an existing Vault path.
- Produces: immutable `BatchExecutionInput`, `ExecutionItem`, `ExecutionPolicy`, `BatchExecutionContractError`, and `sha256_file(path)`.

- [ ] **Step 1: Write failing strict-schema tests**

```python
batch = load_batch_plan(plan_path, digest)
assert [item.identity for item in batch.items] == ["ru-RU:m1", "en-US:m1"]
assert batch.maximum_active_items == 1
```

Also assert rejection for wrong confirmation, reordered/duplicate derivative keys, mutated plan/metadata/video hashes, non-YouTube targets, public jobs, missing Credential IDs and missing Vault files.

- [ ] **Step 2: Run contracts tests and observe RED**

Run: `C:\Users\eugen\OneDrive\Documents\video\tools\.venv\Scripts\python.exe -m pytest --import-mode=importlib tests/publication_batch_execution_mvp/test_contracts.py -q`

Expected: import failure for `publication_batch_execution`.

- [ ] **Step 3: Implement exact parsing and full preflight**

```python
@dataclass(frozen=True)
class ExecutionItem:
    ordinal: int
    identity: str
    plan_path: Path
    plan_sha256: str
    derivative_path: Path
    derivative_sha256: str
    credential_id: str
```

Reject unless the aggregate keys, child plan hashes, video/metadata lineage, job ordinals and platform/account/credential coverage all match exactly. Do not open the Vault or start a child during parsing.

- [ ] **Step 4: Run contract tests and verify GREEN**

- [ ] **Step 5: Commit the contracts**

```powershell
git add apps/publication-batch-execution/publication_batch_execution tests/publication_batch_execution_mvp/test_contracts.py
git commit -m "feat: define publication batch execution contracts"
```

### Task 3: Build the durable strict-serial execution owner

**Files:**
- Create: `apps/publication-batch-execution/publication_batch_execution/operation.py`
- Test: `tests/publication_batch_execution_mvp/test_operation.py`

**Interfaces:**
- Consumes: `PublicationBatchExecution.execute(batch, vault_path, output_dir, operation_id, executor, on_log)` and executor method `execute(item, output_dir, child_operation_id, vault_path, on_log) -> ChildExecutionFact`.
- Produces: `BatchExecutionResult(result_class, receipt_path, manifest_path, error)` plus atomic receipt and aggregate JSON.

- [ ] **Step 1: Write failing lifecycle tests**

```python
first = operation.execute(batch, vault, output, "op-1", executor)
replay = operation.execute(batch, vault, output, "op-1", executor)
assert first.result_class == "COMPLETED"
assert replay.result_class == "DUPLICATE_COMPLETED"
assert executor.maximum_active == 1
```

Cover conflict, corrupt receipt, stale completed child, continue-after-failure, partial resume, unknown continuation, unknown replay fencing, no aggregate on partial failure and atomic cleanup.

- [ ] **Step 2: Run operation tests and observe RED**

Run: `C:\Users\eugen\OneDrive\Documents\video\tools\.venv\Scripts\python.exe -m pytest --import-mode=importlib tests/publication_batch_execution_mvp/test_operation.py -q`

- [ ] **Step 3: Implement the continuation state machine**

Use stable item roots `items/{ordinal:04d}-{plan_sha[:12]}`, stable child IDs derived from parent/ordinal/plan hash, `maximumActiveItems: 1`, atomic temporary-file replacement and hash-verified child reuse. Preserve `UNKNOWN` rows and never pass them back to the executor.

- [ ] **Step 4: Run operation tests and verify GREEN**

- [ ] **Step 5: Commit the owner**

```powershell
git add apps/publication-batch-execution/publication_batch_execution/operation.py tests/publication_batch_execution_mvp/test_operation.py
git commit -m "feat: add resumable publication batch execution"
```

### Task 4: Compose Publication through its public launcher

**Files:**
- Create: `apps/publication-batch-execution/publication_batch_execution/child_executor.py`
- Create: `apps/publication-batch-execution/publication_batch_execution/cli.py`
- Create: `apps/publication-batch-execution/run.ps1`
- Create: `apps/publication-batch-execution/install.ps1`
- Create: `apps/publication-batch-execution/mvp.json`
- Create: `apps/publication-batch-execution/README.md`
- Test: `tests/publication_batch_execution_mvp/test_child_executor.py`
- Test: `tests/publication_batch_execution_mvp/test_cli.py`

**Interfaces:**
- Consumes: `apps/publication/run.ps1 execute C:\Jobs\item\publication-plan.json --confirmation 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef --credential-vault C:\Users\creator\vault.json --output-dir C:\Jobs\execution\items\0001-0123456789ab --operation-id batch-op:0001:0123456789ab --json`.
- Produces: independently verified `ChildExecutionFact` and CLI result classes matching the operation.

- [ ] **Step 1: Write failing launcher/CLI tests**

Assert argv-only invocation, exact child confirmation, stable output, no secret arguments, strict receipt schema, external-ID validation, `UNKNOWN` preservation and `doctor` reporting `childOwner: publication`.

- [ ] **Step 2: Run child/CLI tests and observe RED**

Run: `C:\Users\eugen\OneDrive\Documents\video\tools\.venv\Scripts\python.exe -m pytest --import-mode=importlib tests/publication_batch_execution_mvp/test_child_executor.py tests/publication_batch_execution_mvp/test_cli.py -q`

- [ ] **Step 3: Implement streaming child execution and public launchers**

The executor reads Publication's JSON result and then independently checks `publication-receipt.json` plus `publication-manifest.json`; it accepts completion only with exact plan hash and a non-empty private YouTube external ID. It maps `UNKNOWN` and `REJECTED_UNKNOWN` without retrying or persisting child output.

- [ ] **Step 4: Add adjacent real-owner composition test**

Use real Publication and Credential Vault launchers with a fake Platform I/O launcher. Store a test secret through Vault, execute two child plans, assert strict order, distinct external IDs, aggregate coverage and absence of the secret from every parent artifact.

- [ ] **Step 5: Run all new MVP tests and verify GREEN**

Run: `C:\Users\eugen\OneDrive\Documents\video\tools\.venv\Scripts\python.exe -m pytest --import-mode=importlib tests/publication_batch_execution_mvp -q`

- [ ] **Step 6: Commit the runnable MVP**

```powershell
git add apps/publication-batch-execution tests/publication_batch_execution_mvp
git commit -m "feat: compose publication batch execution"
```

### Task 5: Add the separate Studio Release Execute Graph

**Files:**
- Modify: `apps/video-graph-studio/studio/api.py`
- Modify: `apps/video-graph-studio/studio/adapters.py`
- Modify: `apps/video-graph-studio/studio/server.py`
- Modify: `apps/video-graph-studio/web/index.html`
- Modify: `apps/video-graph-studio/web/app.js`
- Modify: `apps/video-graph-studio/web/styles.css`
- Modify: `apps/video-graph-studio/README.md`
- Create: `tests/video_graph_studio/test_publication_batch_execution_graph.py`
- Modify: `tests/video_graph_studio/test_web_shell.py`

**Interfaces:**
- Consumes: completed same-RunStore `folder-release`/`url-release` run, exact `plan-publication-batch` manifest hash and home-confined Vault path.
- Produces: Graph `publication-batch-execute` with nodes `execute-publication-batch` and `verify-publication-batch-execution`.

- [ ] **Step 1: Write failing Graph/admission/adapter/web tests**

```python
assert [node["type"] for node in run["graph"]["nodes"]] == [
    "execute-publication-batch", "verify-publication-batch-execution"
]
```

Reject an incomplete source run, wrong graph type, wrong SHA, unsupported target inside the aggregate, non-home Vault and missing verified planning fact. Assert the browser exposes Release Execute fields and two-step progress.

- [ ] **Step 2: Run Studio tests and observe RED**

Run: `C:\Users\eugen\OneDrive\Documents\video\tools\.venv\Scripts\python.exe -m pytest --import-mode=importlib tests/video_graph_studio/test_publication_batch_execution_graph.py tests/video_graph_studio/test_web_shell.py -q`

- [ ] **Step 3: Implement Graph admission, adapters and browser projection**

The execute adapter calls only the new public launcher. The verifier independently checks aggregate hash, every child manifest/hash, exact source-batch coverage, private YouTube external IDs and maximum concurrency one.

- [ ] **Step 4: Run full Studio tests and verify GREEN**

Run: `C:\Users\eugen\OneDrive\Documents\video\tools\.venv\Scripts\python.exe -m pytest --import-mode=importlib tests/video_graph_studio -q`

- [ ] **Step 5: Commit Studio composition**

```powershell
git add apps/video-graph-studio tests/video_graph_studio
git commit -m "feat: add release batch execution graph"
```

### Task 6: Register, document and verify delivery evidence

**Files:**
- Modify: `README.md`
- Modify: `TOOLS.md`
- Modify: `apps/README.md`
- Modify: `docs/PROJECT_MAP.md`
- Modify: `docs/WORKFLOWS.md`
- Modify: `docs/project/planning/capability-roadmap.md`
- Modify: `docs/project/product/creator-automation-studio.md`
- Modify: `docs/project/architecture/design/blueprints/video-graph-studio.md`
- Modify: `docs/project/evidence/README.md`
- Modify: `docs/project/evidence/video-graph-studio/delivery-ledger.md`
- Create: `docs/mvp/publication-batch-execution/vertical-slice-brief.md`
- Create: `docs/mvp/publication-batch-execution/capability-dag.md`
- Create: `docs/mvp/publication-batch-execution/capability-evidence.md`
- Create: `docs/mvp/publication-batch-execution/delivery-ledger.md`
- Create: `docs/project/evidence/publication-batch-execution/delivery-ledger.md`
- Create: `docs/project/evidence/video-graph-studio/publication-batch-execution-graph-drill.md`
- Create: `docs/training/15-publication-batch-execution.md`
- Modify: `scripts/test-all.ps1`
- Modify: `tests/repository/test_repository_layout.py`

**Interfaces:**
- Consumes: verified CLI, operation and Studio evidence from Tasks 1–5.
- Produces: registered 25th independent MVP and evidence-bounded documentation.

- [ ] **Step 1: Register the suite and repository layout**

Add `tests\publication_batch_execution_mvp` to `scripts/test-all.ps1`, add `publication-batch-execution` to layout expectations and update the README test count only from the actual final output.

- [ ] **Step 2: Write the four required MVP artifacts and product documentation**

Record `DOMAIN_VERIFIED`; name the real Public Publication/Vault + fake Platform I/O substitute; explicitly list missing authenticated batch upload, reconciliation, other-platform private adapters, hosted/mobile and production evidence.

- [ ] **Step 3: Run a real browser/API composition drill without starting execution**

Create a valid completed Release planning fixture in an isolated local Studio data root, admit `publication-batch-execute`, inspect the two-node browser projection at 1280×720 and record exact run ID, hashes and non-execution boundary.

- [ ] **Step 4: Run the complete verification gate**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\test-all.ps1
node --check apps/video-graph-studio/web/app.js
python -m compileall -q apps/publication-batch-execution apps/video-graph-studio tests/publication_batch_execution_mvp
git diff --check
```

Also parse the new PowerShell scripts, run installer `doctor`, scan intended changes for credential-shaped text and confirm the unrelated user file is untracked.

- [ ] **Step 5: Commit, push, open a ready PR and merge to `main`**

```powershell
git add README.md TOOLS.md apps/README.md apps/publication apps/publication-batch-execution apps/video-graph-studio video_platform/cli.py docs/PROJECT_MAP.md docs/WORKFLOWS.md docs/mvp/publication-batch-execution docs/project docs/training/15-publication-batch-execution.md scripts/test-all.ps1 tests/publication_mvp tests/publication_batch_execution_mvp tests/repository/test_repository_layout.py tests/video_graph_studio tests/video_platform/test_cli.py
git commit -m "feat: add publication batch execution graph"
git push -u origin codex/publication-batch-execution
```

Create a ready PR against `main`, merge only after fresh full verification, fetch `origin/main`, compare tree hashes and delete the remote feature branch.
