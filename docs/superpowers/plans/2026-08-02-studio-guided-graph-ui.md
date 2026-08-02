# Studio Guided Graph UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Subagents are prohibited for this project; execute every checkbox inline and review at each commit.

**Goal:** Replace the misleading fixed three-card ComfyUI imitation with a guided builder that shows the exact admitted Graph, its sequential Loops, actionable readiness, and only controls that really work.

**Architecture:** The API projects an immutable Workflow Catalog from the same `GraphDefinition` objects used for admission. A pure browser model groups templates into creator outcomes, resolves Folder/URL variants, computes readiness, and projects node status. The DOM layer renders a guided configuration rail and exact dynamic Graph; RunStore and every child MVP retain their existing ownership.

**Tech Stack:** Python 3.12, PowerShell 5.1, browser-native ES modules, Node 22 test runner, HTML/CSS, existing loopback HTTP server and pytest suite.

## Global Constraints

- Keep maximum active workflow count and child-process count at one.
- Do not add arbitrary node insertion, edge editing, drag persistence, or user-authored graph execution.
- Do not move child continuation state into Video Graph Studio.
- Preserve current versioned create/start/cancel commands and all existing template IDs.
- Keep the server bound to `127.0.0.1` and preserve secure-workspace scopes.
- Do not read, edit, stage, or commit `apps/localization/localizer/subagent_translation.py`.
- Use `apply_patch` for repository file edits and no subagents.

---

### Task 1: Workflow Catalog Projection

**Files:**
- Create: `apps/video-graph-studio/studio/workflow_catalog.py`
- Modify: `apps/video-graph-studio/studio/api.py`
- Create: `tests/video_graph_studio/test_workflow_catalog.py`

**Interfaces:**
- Consumes: `dict[str, GraphDefinition]` keyed by the existing public `templateId`.
- Produces: `build_workflow_catalog(graphs) -> list[dict[str, object]]` where every row contains `templateId`, `goalId`, `group`, `title`, `summary`, `sourceKind`, `effect`, `revision`, `nodes`, and `edges`.
- `GET /api/v1/capabilities` continues to return `contractVersion` plus `capabilities`, now as the exact workflow projection.

- [ ] **Step 1: Write the failing catalog contract test**

  Add tests that call the real `StudioApplication` API and assert that `url-translation` exposes exactly six ordered nodes, five typed Fact edges, the `translation` Loop, and `planning-only`/`local-only` effect metadata as appropriate. Iterate every returned row and compare its node IDs and edge dictionaries with the corresponding real Graph definition.

- [ ] **Step 2: Run the RED test**

  Run:

  ```powershell
  C:\Users\eugen\OneDrive\Documents\video\tools\.venv\Scripts\python.exe -m pytest --import-mode=importlib tests/video_graph_studio/test_workflow_catalog.py -q
  ```

  Expected: fail because `/api/v1/capabilities` still returns three legacy capability rows without template or graph structure.

- [ ] **Step 3: Implement the immutable projection**

  Define literal workflow metadata for all existing templates and literal node-type metadata with creator-facing titles, unique owner, relationship, Loop, retry description, and output fact. Validate that metadata covers every supplied template and node type exactly. Build nodes and edges directly from `GraphDefinition.to_dict()`; never reconstruct topology from client copy.

- [ ] **Step 4: Expose the real catalog**

  Assemble one `ALL_WORKFLOW_GRAPHS` mapping in `api.py`, mapping `prepared-localization` to `PREPARED_FOLDER_GRAPH` and every other public template ID to its current Graph. Replace `_capabilities()` with `build_workflow_catalog(ALL_WORKFLOW_GRAPHS)`.

- [ ] **Step 5: Run focused and adjacent tests**

  Run the new test plus `tests/video_graph_studio/test_api.py`, `test_intake_graph.py`, and `test_contract_discovery.py`. Expected: all pass and current create/start behavior remains unchanged.

- [ ] **Step 6: Commit**

  ```powershell
  git add apps/video-graph-studio/studio/workflow_catalog.py apps/video-graph-studio/studio/api.py tests/video_graph_studio/test_workflow_catalog.py
  git commit -m "feat: project the Studio workflow catalog"
  ```

### Task 2: Browser Draft Graph and Readiness Model

**Files:**
- Create: `apps/video-graph-studio/web/workflow-model.mjs`
- Create: `tests/video_graph_studio/workflow_model.test.mjs`
- Create: `tests/video_graph_studio/test_workflow_model.py`

**Interfaces:**
- Produces: `groupWorkflowGoals(catalog)`, `resolveTemplate(catalog, goalId, sourceKind)`, `evaluateReadiness(input)`, `projectGraph(workflow, run)`, and `nextZoom(current, direction)`.
- `evaluateReadiness` returns `{ready:boolean, checks:Array<{id,label,status,detail}>}` and never mutates DOM or server state.
- `projectGraph` returns exact catalog nodes decorated only with RunStore status; it never invents completion.

- [ ] **Step 1: Write Node behavior tests**

  Use literal catalog and run fixtures. Assert that Folder/URL variants group under one goal, unsupported source variants reject, contract/health/source/language blockers are independently visible, platform-contact effects survive projection, a ten-node run keeps ten nodes in order, and zoom clamps between 60 and 140 percent.

- [ ] **Step 2: Add a pytest launcher and observe RED**

  The Python test invokes `node --test tests/video_graph_studio/workflow_model.test.mjs` and asserts exit code zero. Run it and observe failure because `workflow-model.mjs` does not exist.

- [ ] **Step 3: Implement the pure model**

  Implement only the exported functions required by the tests. Use no DOM globals, storage, network calls, or timers.

- [ ] **Step 4: Run GREEN and mutation checks**

  Run the pytest launcher. Temporarily reason through mutations for missing contract blocker, wrong source variant, reordered node projection, and over-limit zoom; each must break a named test.

- [ ] **Step 5: Commit**

  ```powershell
  git add apps/video-graph-studio/web/workflow-model.mjs tests/video_graph_studio/workflow_model.test.mjs tests/video_graph_studio/test_workflow_model.py
  git commit -m "feat: add the Studio draft graph model"
  ```

### Task 3: Guided Builder Shell

**Files:**
- Modify: `apps/video-graph-studio/web/index.html`
- Modify: `apps/video-graph-studio/web/styles.css`
- Modify: `tests/video_graph_studio/test_web_shell.py`

**Interfaces:**
- Provides stable regions: `workflow-goal`, `source-kind-controls`, `workflow-summary`, `readiness-list`, `reconnect-button`, `graph-track`, `zoom-level`, and the existing configuration field IDs consumed by the DOM controller.
- Removes misleading `capability-palette`, connection ports, insert `+` glyphs, and select-tool control.

- [ ] **Step 1: Write the failing shell/accessibility test**

  Assert that the shell exposes a labelled outcome select, source-kind controls, persistent readiness region, reconnect action, dynamic graph track, real zoom labels and explanatory empty state. Assert that insert glyphs, ports, select tool, and nineteen template radios are absent.

- [ ] **Step 2: Run RED**

  Run `test_web_shell.py`; expect failure on the missing guided-builder regions and presence of misleading controls.

- [ ] **Step 3: Replace the shell structure**

  Move configuration into a scrollable left builder rail, retain existing field IDs/dialogs, create a dynamic center graph track, and simplify the right Inspector. Use plain-language headings and keep the activity log.

- [ ] **Step 4: Implement responsive visual hierarchy**

  Replace one-line minified layout rules with focused builder, workflow-card, readiness, graph-lane, node, edge, Inspector and mobile rules. At 1280 pixels the builder, canvas and Inspector must fit without document overflow; the graph track may scroll internally.

- [ ] **Step 5: Run GREEN and commit**

  Run `test_web_shell.py` and commit the shell independently.

### Task 4: Catalog-driven DOM Composition

**Files:**
- Modify: `apps/video-graph-studio/web/app.js`
- Modify: `apps/video-graph-studio/web/index.html`
- Modify: `tests/video_graph_studio/test_web_shell.py`

**Interfaces:**
- Consumes: `GET /api/v1/contracts`, `GET /api/v1/health`, `GET /api/v1/capabilities`, and pure functions from `workflow-model.mjs`.
- Preserves: current payload schemas and create/start/cancel envelopes.
- Produces: dynamic exact graph nodes, typed edges, node Inspector projection, readiness checks, reconnect behavior, working zoom/fit controls, and visible API admission errors.

- [ ] **Step 1: Add failing controller-boundary assertions**

  Require ES-module loading, catalog query, model imports, event delegation for dynamic nodes, explicit reconnect handler, and no static three-node copy map. Run `test_web_shell.py` and observe RED.

- [ ] **Step 2: Refactor bootstrap into explicit connection states**

  Load contracts, health, catalog and recent runs independently. Preserve detailed failure text. Reconnect repeats these queries without clearing the draft. Disable mutation until all relevant readiness checks pass.

- [ ] **Step 3: Render outcome/source/configuration from catalog facts**

  Populate grouped outcome options, resolve the exact template ID from goal/source kind, show only relevant existing inputs, and update persistent readiness on every input/change event.

- [ ] **Step 4: Render exact graph and Inspector**

  Create one DOM node per catalog node, one typed edge between adjacent nodes, Loop badges, step numbering and real RunStore status. Node click only selects and explains; no insertion affordance exists.

- [ ] **Step 5: Implement real fit and zoom**

  Use `nextZoom` for buttons, update `--graph-zoom` and `zoom-level`, and calculate fit from viewport width and node count. Verify each action changes the visible scale label and graph transform.

- [ ] **Step 6: Preserve submission and run polling**

  Reuse the existing payload construction and exact contract envelopes. After create/start, project run statuses onto exact nodes and leave Draft Graph controls available for queueing another run.

- [ ] **Step 7: Run focused tests and commit**

  Run web shell, workflow model, workflow catalog and all Studio tests. Commit only after they pass.

### Task 5: Launcher Truth and Live Browser Evidence

**Files:**
- Modify: `apps/video-graph-studio/run.ps1`
- Modify: `tests/video_graph_studio/test_contract_discovery.py`
- Modify: `apps/video-graph-studio/README.md`
- Modify: `docs/mvp/video-graph-studio/capability-dag.md`
- Modify: `docs/mvp/video-graph-studio/capability-evidence.md`
- Modify: `docs/mvp/video-graph-studio/delivery-ledger.md`
- Create: `docs/project/evidence/video-graph-studio/guided-graph-ui-drill.md`

**Interfaces:**
- Launcher starts from the application root so `studio.server` cannot resolve to another installed or stale package.
- Browser reports healthy, contract-ready, catalog-ready and input-ready as separate facts.

- [ ] **Step 1: Add a failing launch-boundary test**

  Start the public launcher on an ephemeral port, request `/api/v1/contracts` and `/api/v1/capabilities`, and assert both return the current contract/catalog shape. This test catches a launcher resolving the wrong `studio` package.

- [ ] **Step 2: Harden the launcher**

  Execute Python with the application root as working directory while preserving and restoring caller state. Keep `PYTHONPATH`, loopback binding and current arguments. Surface bind/start errors; never silently reuse an incompatible listener.

- [ ] **Step 3: Restart and exercise the real page**

  Stop only the verified listener on port 8765, launch the new server, reload the existing page, and exercise URL → Dub, source URL, language selection, reconnect, zoom, fit, node inspection, and a safe local/non-platform create/start path.

- [ ] **Step 4: Record evidence honestly**

  Capture viewport size, document/client widths, workflow/node counts, zoom transitions, readiness checks, created run ID, node order and terminal result. Record missing authenticated-upload, mobile and production evidence.

- [ ] **Step 5: Run full verification**

  Run Studio tests, Node syntax/tests, public launcher contract checks, `scripts/test-all.ps1`, manifest validation, and `git diff --check`.

- [ ] **Step 6: Commit, push, PR and merge**

  Stage only the guided UI files, preserve the unrelated untracked localization file, push `codex/studio-guided-graph-ui`, open a ready PR against `main`, merge after clean verification, and confirm the remote `main` SHA.
