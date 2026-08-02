# Resource Budget MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a durable independent owner that prevents local cross-process byte/slot reservation oversubscription per workspace.

**Architecture:** A standard-library Python CLI owns one SQLite database. Every mutation starts `BEGIN IMMEDIATE`, reclaims expired leases, checks invariants and commits one bounded result; Studio and Workspace Storage integrate only through public commands.

**Tech Stack:** Python 3.12 standard library, SQLite, PowerShell 5.1, pytest.

## Global Constraints

- Do not import another MVP's private implementation.
- Keep one authoritative writer for budget configuration and leases.
- Preserve the unrelated untracked `apps/localization/localizer/subagent_translation.py`.
- Do not use subagents.
- Do not claim distributed or production enforcement.

---

### Task 1: Durable reservation owner

**Files:**
- Create: `tests/resource_budget_mvp/test_budget.py`
- Create: `apps/resource-budget/resource_budget/budget.py`

**Interfaces:**
- Produces: `ResourceBudget.configure`, `reserve`, `renew`, `release`, `snapshot`; `BudgetResult`; `BudgetError`.

- [ ] Write failing tests for configuration replay/conflict, hard byte/slot denial, duplicate/conflict, generation staleness, release and TTL reclamation.
- [ ] Run `python -m pytest --import-mode=importlib tests/resource_budget_mvp/test_budget.py -q` and confirm missing-module failure.
- [ ] Implement SQLite schema and transactional methods with `BEGIN IMMEDIATE`.
- [ ] Run the focused suite and confirm it passes.

### Task 2: Public CLI and cross-process proof

**Files:**
- Create: `tests/resource_budget_mvp/test_cli.py`
- Create: `apps/resource-budget/resource_budget/cli.py`
- Create: `apps/resource-budget/run.ps1`
- Create: `apps/resource-budget/install.ps1`

**Interfaces:**
- Consumes: the Task 1 public owner.
- Produces: JSON result classes and stable exit codes for all commands.

- [ ] Write failing CLI lifecycle and concurrent-reservation tests using two real processes.
- [ ] Confirm failure because the CLI is missing.
- [ ] Implement argparse commands and launchers.
- [ ] Run the focused CLI suite and confirm only one competing reservation succeeds.

### Task 3: Independent evidence and repository integration

**Files:**
- Create: `apps/resource-budget/{README.md,mvp.json}`
- Create: `docs/mvp/resource-budget/{vertical-slice-brief.md,capability-dag.md,capability-evidence.md,delivery-ledger.md}`
- Create: `docs/project/evidence/resource-budget/delivery-ledger.md`
- Create: `scripts/drills/resource-budget.ps1`
- Modify: repository/application/project indexes and `scripts/test-all.ps1`.

**Interfaces:**
- Consumes: public Resource Budget CLI and Workspace Storage capacity CLI.
- Produces: reproducible adjacent-integration evidence and the 20th MVP manifest.

- [ ] Run a real Workspace Storage capacity query, configure the returned available-byte policy, reserve/reject/release/reclaim, and record exact evidence.
- [ ] Update architecture, capability map, roadmap, README badges and evidence indexes.
- [ ] Run the full repository suite, manifest validation, compile/PowerShell parsing and `git diff --check`.
- [ ] Commit, push, open and merge a PR only after fresh verification.

## Self-review

The plan covers every design invariant and failure class. Names are consistent across tasks. No placeholders or private cross-MVP imports are present. Inline execution is selected because the user prohibited subagents and authorized autonomous continuation.
