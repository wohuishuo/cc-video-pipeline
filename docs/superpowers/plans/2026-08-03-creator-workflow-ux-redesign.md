# Creator Workflow UX Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the seven-stage Creator Workflow Studio readable and self-explanatory without changing any backend or workflow contracts.

**Architecture:** Preserve the vanilla HTML/CSS/ES-module stack. Put deterministic launch and navigation presentation in `creator-workspace-model.mjs`, render it from `app.js`, and use semantic HTML plus a tokenized CSS refresh for hierarchy and responsive behavior.

**Tech Stack:** HTML5, vanilla CSS, browser ES modules, Node test runner, Python pytest, loopback Studio browser drill.

## Global Constraints

- Keep every existing API payload and stable DOM ID.
- Keep the seven stages and dark theme.
- Use one electric-blue accent and no decorative gradients or glows.
- Do not add dependencies or use subagents.
- Use TDD for every new JavaScript behavior.

---

### Task 1: Deterministic navigation and launch presentation

**Files:**
- Modify: `apps/video-graph-studio/web/creator-workspace-model.mjs`
- Modify: `tests/video_graph_studio/creator_workspace_model.test.mjs`

**Interfaces:**
- Produces: `stageAction(stage, facts)` returning `{ label, hint }`.
- Produces: `launchPresentation(readiness, hasActiveRun)` returning `{ state, title, description, buttonLabel, action }`.

- [ ] Write failing model tests for specific stage labels, blocked setup, ready launch, and active-run progress.
- [ ] Run `node --test tests/video_graph_studio/creator_workspace_model.test.mjs` and confirm failures identify missing exports.
- [ ] Implement the two pure helpers with literal Chinese presentation strings.
- [ ] Run the focused Node suite and confirm it passes.
- [ ] Commit as `feat: clarify studio workflow actions`.

### Task 2: Review and navigation semantics

**Files:**
- Modify: `apps/video-graph-studio/web/index.html`
- Modify: `apps/video-graph-studio/web/app.js`
- Modify: `tests/video_graph_studio/test_web_shell.py`

**Interfaces:**
- Consumes: `stageAction` and `launchPresentation` from Task 1.
- Preserves: existing stage, form, review, and launch element IDs.

- [ ] Add failing shell assertions for the review state title/description, edit controls, and stage action copy anchors.
- [ ] Run `pytest tests/video_graph_studio/test_web_shell.py -q` and confirm the new structure is absent.
- [ ] Replace numbered English eyebrows with Chinese task labels and add review status/edit affordances.
- [ ] Render stage-specific footer copy and make the launch button route to Activity when a run is active.
- [ ] Run shell and Node tests and confirm they pass.
- [ ] Commit as `feat: make studio review actionable`.

### Task 3: Product-interface visual system

**Files:**
- Modify: `apps/video-graph-studio/web/styles.css`
- Modify: `apps/video-graph-studio/web/index.html`

**Interfaces:**
- Consumes the DOM structure from Task 2.
- Produces responsive layout at desktop, 800x900, and 390x844.

- [ ] Replace typography, spacing, surface, button, focus, selected, disabled, and status tokens while keeping a single dark theme.
- [ ] Recompose the stage rail, stage header, selection cards, footer, review workload strip, configuration list, and launch panel.
- [ ] Add reduced-motion and compact-width rules; ensure no control text wraps on desktop.
- [ ] Run `node --check apps/video-graph-studio/web/app.js`, Node tests, shell tests, and `git diff --check`.
- [ ] Commit as `style: redesign creator workflow studio`.

### Task 4: Real-browser verification and evidence

**Files:**
- Modify: `docs/project/evidence/video-graph-studio/local-first-creator-workspace-drill.md`
- Modify: `docs/project/evidence/video-graph-studio/delivery-ledger.md`

**Interfaces:**
- Uses the real loopback server and saved creator/local state.
- Produces visual and interaction evidence only; it does not start media rendering.

- [ ] Start Studio from this worktree and reload the existing in-app browser tab.
- [ ] Walk all seven stages and verify labels, selected states, edit actions, blocked/ready/running presentation, and local-only output.
- [ ] Verify desktop, 800x900, and 390x844 layouts have no document overflow.
- [ ] Confirm zero browser console errors and record the observed facts.
- [ ] Run `scripts/test-all.ps1`, all Node tests, manifest validation, and `git diff --check`.
- [ ] Commit evidence, push the branch, open a PR, and merge to `main` after the final verification gate.
