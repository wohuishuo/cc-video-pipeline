# Partial Creator Catalog Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let creators retry complete Douyin discovery with the prior local cookie reference and explicitly process selected videos from a truthful incomplete catalog.

**Architecture:** Creator Discovery continues to own catalog completeness. Studio restores only the previously committed authentication-file path for retries. Campaign admission accepts an incomplete manifest only when the versioned request carries `allowPartialCatalog: true`; Creator Selection still verifies exact IDs and lineage before batch processing.

**Tech Stack:** Python 3.12 standard library, SQLite-backed Studio API, vanilla JavaScript model/UI, Node test runner, pytest.

## Global Constraints

- Never change `complete=false` or `truncated=true` on a partial Creator Manifest.
- Never read cookie contents into browser state or logs.
- Omitted or false `allowPartialCatalog` preserves strict rejection.
- Empty or unknown selected IDs remain rejected.
- No browser-session scraping or simulated scrolling in this slice.

---

### Task 1: Versioned partial-catalog admission

**Files:**
- Modify: `tests/video_graph_studio/test_creator_campaign_graph.py`
- Modify: `apps/video-graph-studio/studio/api.py`

**Interfaces:**
- Consumes: `POST /api/v1/runs`, `templateId="creator-campaign"`, verified Creator Manifest.
- Produces: persisted `parameters.allowPartialCatalog: bool` and a Campaign run only when consent is explicit.

- [ ] **Step 1: Write the failing API test**

```python
def test_creator_campaign_accepts_explicit_partial_catalog_selection(tmp_path):
    manifest = _creator_manifest(tmp_path, complete=False, truncated=True)
    store = RunStore(tmp_path / "studio.db")
    creator_run_id = _completed_creator_run(store, manifest)
    app = StudioApplication(store, WorkflowEngine(store, {}), allowed_roots=(tmp_path,))
    payload = _payload(creator_run_id)
    payload["allowPartialCatalog"] = True
    status, response = app.handle("POST", "/api/v1/runs", {}, _envelope(payload))
    run = store.get_run(response["value"]["runId"])
    assert status == 201
    assert run["parameters"]["allowPartialCatalog"] is True
```

- [ ] **Step 2: Run the focused test and observe `REJECTED_MALFORMED`**

Run: `python -m pytest --import-mode=importlib tests/video_graph_studio/test_creator_campaign_graph.py -q`

- [ ] **Step 3: Implement the minimal policy gate**

```python
allow_partial = payload.get("allowPartialCatalog") is True
if (not catalog["complete"] or catalog["truncated"]) and not allow_partial:
    raise ContractError(
        "REJECTED_CONFLICT",
        "creator campaign requires a complete creator catalog or explicit partial-catalog consent",
    )
parameters["allowPartialCatalog"] = allow_partial
```

- [ ] **Step 4: Run the focused suite and commit**

```powershell
python -m pytest --import-mode=importlib tests/video_graph_studio/test_creator_campaign_graph.py -q
git commit -am "feat: admit explicit partial creator selections"
```

### Task 2: Browser consent and cookie-path recovery

**Files:**
- Modify: `tests/video_graph_studio/creator_workspace_model.test.mjs`
- Modify: `tests/video_graph_studio/test_web_shell.py`
- Modify: `apps/video-graph-studio/web/creator-workspace-model.mjs`
- Modify: `apps/video-graph-studio/web/index.html`
- Modify: `apps/video-graph-studio/web/app.js`
- Modify: `apps/video-graph-studio/web/styles.css`

**Interfaces:**
- Consumes: restored completed creator-profile run parameters and partial Creator Catalog projection.
- Produces: `state.allowPartialCatalog`, `payload.allowPartialCatalog`, visible consent control and restored authentication-file path.

- [ ] **Step 1: Write failing model tests**

```javascript
assert.deepEqual(campaignReadiness({...state, catalog: partial, allowPartialCatalog: true}), {ready:true, missing:[]});
assert.equal(buildCampaignPayload({...state, allowPartialCatalog:true}).allowPartialCatalog, true);
```

- [ ] **Step 2: Run Node tests and observe the complete-catalog blocker**

Run: `node --test tests/video_graph_studio/creator_workspace_model.test.mjs`

- [ ] **Step 3: Implement consent in the pure model**

```javascript
if (state.catalog && (!state.catalog.complete || state.catalog.truncated) && !state.allowPartialCatalog) {
  missing.push("Load all videos or explicitly process the current catalog");
}
```

- [ ] **Step 4: Write failing shell assertions for the control and cookie restoration**

```python
assert 'id="allow-partial-catalog"' in html
assert 'recent.parameters?.authenticationFile' in script
```

- [ ] **Step 5: Implement the visible warning, checkbox binding and restored path**

```javascript
state.allowPartialCatalog = event.target.checked;
document.querySelector("#authentication-file").value = recent.parameters?.authenticationFile || "";
```

- [ ] **Step 6: Run web/model tests and commit**

```powershell
node --check apps/video-graph-studio/web/app.js
node --test tests/video_graph_studio/*.test.mjs
python -m pytest --import-mode=importlib tests/video_graph_studio/test_web_shell.py -q
git commit -am "feat: let creators process an explicit partial catalog"
```

### Task 3: Evidence and end-to-end verification

**Files:**
- Modify: `apps/video-graph-studio/README.md`
- Modify: `docs/project/evidence/video-graph-studio/local-first-creator-workspace-drill.md`
- Modify: `docs/project/evidence/video-graph-studio/delivery-ledger.md`

**Interfaces:**
- Consumes: complete and partial catalog browser states.
- Produces: executable evidence for truthful fallback admission and current non-goals.

- [ ] **Step 1: Document the two recovery paths**

Record that load-all reuses a local cookie path and that partial processing requires explicit consent without changing catalog completeness.

- [ ] **Step 2: Restart the real loopback server and verify in the browser**

Restore the existing three-item catalog, confirm the Cookie path is populated, select partial processing, select a language and voice provider, and verify that only unrelated missing fields remain. Do not start the expensive media workload.

- [ ] **Step 3: Run the full verification gate**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test-all.ps1
node --test tests/video_graph_studio/*.test.mjs
git diff --check
```

- [ ] **Step 4: Commit and publish**

```powershell
git add apps/video-graph-studio/README.md docs/project/evidence/video-graph-studio
git commit -m "docs: record partial catalog recovery evidence"
git push -u origin codex/partial-catalog-processing
```
