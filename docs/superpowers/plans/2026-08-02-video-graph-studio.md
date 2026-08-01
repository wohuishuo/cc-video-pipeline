# Video Graph Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do not use subagents for this project.

**Goal:** Deliver a local browser control plane that durably creates, starts, observes, resumes and cancels one-at-a-time prepared-folder Edge localization workflows.

**Architecture:** A standard-library Python application owns graph definitions, workflow continuation and append-only logs in SQLite. Existing media MVPs are invoked only through subprocess adapters. A static browser client issues versioned commands and renders read-only projections.

**Tech Stack:** Python 3.12 standard library, SQLite, `http.server`, HTML5, CSS, browser JavaScript, PowerShell, pytest.

## Global Constraints

- Bind the HTTP server only to `127.0.0.1`.
- Execute at most one workflow and one node at a time.
- Use stable operation IDs, canonical input fingerprints and versioned contracts.
- The coordinator owns continuation only; existing applications retain media and platform state.
- Cross-owner continuation consumes committed facts and receipts.
- Keep cookies, tokens, media bytes and absolute secret contents out of SQLite and logs.
- Use the repository Python 3.12 runtime and Windows-native PowerShell.
- Use tests first for every behavior change.

---

### Task 1: Versioned graph contracts and validation

**Files:**
- Create: `apps/video-graph-studio/studio/contracts.py`
- Create: `apps/video-graph-studio/studio/graph.py`
- Create: `apps/video-graph-studio/studio/__init__.py`
- Test: `tests/video_graph_studio/test_graph.py`

**Interfaces:**
- Produces: `GraphDefinition.from_dict(value)`, `GraphDefinition.fingerprint`, `validate_graph(graph) -> tuple[str, ...]`.
- Consumes: JSON-compatible node records `{id, type, config}` and edge records `{source, target, relationship}`.

- [ ] **Step 1: Write a failing deterministic-order test**

```python
def test_graph_validation_returns_deterministic_topological_order():
    graph = GraphDefinition.from_dict(PREPARED_FOLDER_GRAPH)
    assert validate_graph(graph) == ("source", "localize", "verify")
```

- [ ] **Step 2: Run the focused test and observe the missing-module failure**

Run: `python -m pytest tests/video_graph_studio/test_graph.py -q`

- [ ] **Step 3: Implement immutable contracts, canonical SHA-256 fingerprinting and Kahn DAG validation**

`GraphDefinition.from_dict` rejects duplicate node IDs, missing endpoints, self-edges, unsupported relationship types and cycles. Canonical JSON uses sorted keys and compact separators.

- [ ] **Step 4: Add rejection tests and run the focused suite**

Assert duplicate ID, unknown endpoint and cycle inputs raise `ContractError` with stable reason codes.

- [ ] **Step 5: Commit the verified graph capability**

```powershell
git add apps/video-graph-studio/studio tests/video_graph_studio/test_graph.py
git commit -m "feat(graph-studio): validate versioned workflow graphs"
```

### Task 2: Durable workflow run owner

**Files:**
- Create: `apps/video-graph-studio/studio/store.py`
- Test: `tests/video_graph_studio/test_run_store.py`

**Interfaces:**
- Consumes: `CreateRun(operation_id, correlation_id, graph, parameters)`.
- Produces: `RunStore.create_run(command) -> CommandResult`, `get_run(run_id)`, `list_runs()`, `transition(run_id, expected_version, target)` and `commit_step(...)`.

- [ ] **Step 1: Write a failing idempotency test**

```python
def test_same_operation_and_input_returns_original_run(tmp_path):
    store = RunStore(tmp_path / "studio.db")
    first = store.create_run(command("op-1", source="C:/media"))
    replay = store.create_run(command("op-1", source="C:/media"))
    assert replay.result_class == "DUPLICATE_COMPLETED"
    assert replay.value["runId"] == first.value["runId"]
```

- [ ] **Step 2: Observe RED because `RunStore` is absent**

Run: `python -m pytest tests/video_graph_studio/test_run_store.py -q`

- [ ] **Step 3: Implement schema creation and transactional owner methods**

Tables are `operations`, `runs`, `steps` and `run_logs`. SQLite transactions fence operation fingerprint, run version and step version. JSON values are canonical UTF-8 text.

- [ ] **Step 4: Add conflict, stale transition, terminal replay and ordered-log tests**

The same operation ID with different parameters returns `REJECTED_CONFLICT`; wrong expected version returns `REJECTED_CONFLICT`; completed transition replay returns the prior terminal fact.

- [ ] **Step 5: Run focused tests and commit**

```powershell
python -m pytest tests/video_graph_studio/test_run_store.py -q
git add apps/video-graph-studio/studio/store.py tests/video_graph_studio/test_run_store.py
git commit -m "feat(graph-studio): persist idempotent workflow runs"
```

### Task 3: Serial workflow process manager and adapter

**Files:**
- Create: `apps/video-graph-studio/studio/adapters.py`
- Create: `apps/video-graph-studio/studio/engine.py`
- Test: `tests/video_graph_studio/test_engine.py`

**Interfaces:**
- Consumes: a queued run and ordered graph node IDs.
- Produces: `WorkflowEngine.start(run_id)`, `WorkflowEngine.cancel(run_id)`, committed step results and terminal run facts.
- Adapter port: `execute(node, context, on_log, cancel_event) -> AdapterResult`.

- [ ] **Step 1: Write a failing real-process serial-order test**

Use two command nodes that append start/end markers through a real Python child process. Assert node two starts only after node one exits and only one active process is reported.

- [ ] **Step 2: Observe RED because `WorkflowEngine` is absent**

Run: `python -m pytest tests/video_graph_studio/test_engine.py -q`

- [ ] **Step 3: Implement one-worker execution, stable child IDs and output streaming**

The engine owns one daemon worker thread. It transitions steps transactionally, streams bounded lines to `RunLogOwner`, records exit code and requires adapter verification before committing success.

- [ ] **Step 4: Add partial-failure, restart-interruption and idempotent-cancel tests**

Failure preserves earlier completed steps; recovery converts stale `RUNNING` to `INTERRUPTED`; repeated cancel returns the same terminal result; cleanup terminates only the owned process tree.

- [ ] **Step 5: Add the prepared-folder Edge adapter**

`PreparedFolderEdgeAdapter` verifies `<source>/russian/batch-manifest.json`, invokes `apps/localization/edge-russian.ps1`, and verifies `edge-failures.json` contains no failures plus at least one receipt-matched MP4 before returning `COMPLETED`.

- [ ] **Step 6: Run focused tests and commit**

```powershell
python -m pytest tests/video_graph_studio/test_engine.py -q
git add apps/video-graph-studio/studio/adapters.py apps/video-graph-studio/studio/engine.py tests/video_graph_studio/test_engine.py
git commit -m "feat(graph-studio): execute durable workflows serially"
```

### Task 4: Loopback HTTP and filesystem adapters

**Files:**
- Create: `apps/video-graph-studio/studio/api.py`
- Create: `apps/video-graph-studio/studio/server.py`
- Test: `tests/video_graph_studio/test_api.py`

**Interfaces:**
- Consumes: versioned HTTP JSON commands and allowed filesystem roots.
- Produces: `/api/v1/health`, `/capabilities`, `/folders`, `/runs`, `/runs/{id}`, `/runs/{id}/start`, `/runs/{id}/cancel`.

- [ ] **Step 1: Write a failing loopback API test**

Start the real HTTP server on port `0`, call `/api/v1/health` with `urllib.request`, and assert contract version, database status and active worker count.

- [ ] **Step 2: Observe RED because the server does not exist**

Run: `python -m pytest tests/video_graph_studio/test_api.py -q`

- [ ] **Step 3: Implement JSON routing and canonical error mapping**

The HTTP adapter maps domain results to HTTP status without making business decisions. Request bodies are capped at 1 MiB and malformed JSON returns `REJECTED_MALFORMED`.

- [ ] **Step 4: Implement resolved-path folder browsing**

`GET /folders` returns only directories and supported video counts under configured roots. Resolve symlinks and `..` before containment checks. Reject an out-of-root path with HTTP 403.

- [ ] **Step 5: Add API create/replay/conflict/start tests and commit**

```powershell
python -m pytest tests/video_graph_studio/test_api.py -q
git add apps/video-graph-studio/studio/api.py apps/video-graph-studio/studio/server.py tests/video_graph_studio/test_api.py
git commit -m "feat(graph-studio): expose loopback control API"
```

### Task 5: Comfy-style browser projection

**Files:**
- Create: `apps/video-graph-studio/web/index.html`
- Create: `apps/video-graph-studio/web/styles.css`
- Create: `apps/video-graph-studio/web/app.js`
- Test: `tests/video_graph_studio/test_web_shell.py`

**Interfaces:**
- Consumes: only `/api/v1` query projections and commands.
- Produces: source/language/voice/platform controls, graph canvas, node state, inspector, run history and log drawer.

- [ ] **Step 1: Write failing semantic-shell tests**

Assert the served page contains labeled source, language, voice and platform controls; graph, inspector and log regions; no inline event handlers; and a viewport declaration.

- [ ] **Step 2: Observe RED because the static shell is absent**

Run: `python -m pytest tests/video_graph_studio/test_web_shell.py -q`

- [ ] **Step 3: Implement the responsive shell and design tokens**

Use a graphite canvas, near-black panels, indigo selected state, cyan running state, green completed state, amber warning and red failed state. Maintain WCAG-readable contrast and visible keyboard focus.

- [ ] **Step 4: Implement API bindings and SVG graph edges**

Create and start commands use `crypto.randomUUID()`. Poll only while a run is active, render node states from step projections, and stop polling at a terminal state. Platform controls marked unavailable remain disabled with their evidence level visible.

- [ ] **Step 5: Run shell tests and commit**

```powershell
python -m pytest tests/video_graph_studio/test_web_shell.py -q
git add apps/video-graph-studio/web tests/video_graph_studio/test_web_shell.py
git commit -m "feat(graph-studio): add browser workflow canvas"
```

### Task 6: Public application boundary and delivery evidence

**Files:**
- Create: `apps/video-graph-studio/run.ps1`
- Create: `apps/video-graph-studio/install.ps1`
- Create: `apps/video-graph-studio/mvp.json`
- Create: `apps/video-graph-studio/README.md`
- Create: `docs/project/README.md`
- Create: `docs/project/architecture/README.md`
- Create: `docs/project/capabilities/README.md`
- Create: `docs/project/engineering/README.md`
- Create: `docs/project/evidence/video-graph-studio/vertical-slice-brief.md`
- Create: `docs/project/evidence/video-graph-studio/capability-dag.md`
- Create: `docs/project/evidence/video-graph-studio/capability-evidence.md`
- Create: `docs/project/evidence/video-graph-studio/delivery-ledger.md`
- Modify: `apps/README.md`
- Modify: `README.md`
- Test: `tests/video_graph_studio/test_public_app.py`

**Interfaces:**
- Produces: `apps/video-graph-studio/run.ps1 [-Port 8765] [-NoBrowser] [-DataRoot path]`.
- Consumes: repository Python runtime, the static web directory and public localization launcher.

- [ ] **Step 1: Write a failing public-boundary test**

Assert manifest fields and referenced launcher/installer exist, the README documents start/stop/data behavior, and repository manifest validation discovers the app.

- [ ] **Step 2: Observe RED for the missing public app**

Run: `python -m pytest tests/video_graph_studio/test_public_app.py -q`

- [ ] **Step 3: Implement launcher, installer, manifest and user documentation**

The launcher selects the repository Python 3.12 runtime, starts the loopback server, opens the browser unless `-NoBrowser`, writes runtime state below the configured data root, and handles Ctrl+C cleanup.

- [ ] **Step 4: Record capability artifacts and honest delivery level**

Use `IMPLEMENTED` until real HTTP, process and browser smoke receipts exist. Use `DOMAIN_VERIFIED` only after focused and adjacent tests pass. External Edge success and authenticated platform publication remain explicit missing evidence.

- [ ] **Step 5: Run repository and focused verification**

```powershell
python -m pytest tests/video_graph_studio -q
python scripts/validate_mvp_manifests.py .
powershell -NoProfile -ExecutionPolicy Bypass -File apps/video-graph-studio/run.ps1 -NoBrowser -Port 0
```

- [ ] **Step 6: Inspect the browser at desktop and narrow widths, save a screenshot receipt, and commit**

```powershell
git add apps/video-graph-studio tests/video_graph_studio docs/project README.md apps/README.md
git commit -m "feat: deliver local video graph studio MVP"
```

## Plan self-review

- The plan covers all first-slice requirements from the accepted design.
- Every production behavior begins with an explicit failing test.
- Contract type names and method names are consistent across tasks.
- Raw intake, URL adapters, authenticated publication, arbitrary graph authoring and commercial identity remain separate later plans.
- No subagent execution is permitted; the current task executes each Loop sequentially.

