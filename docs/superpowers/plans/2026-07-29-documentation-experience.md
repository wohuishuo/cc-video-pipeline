# Documentation Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a visual GitHub-native README and a complete English documentation set for the independent video MVP monorepo.

**Architecture:** Keep the root README concise and navigational, with Mermaid diagrams for relationships. Put durable architecture, workflows, and contribution rules in focused `docs/` pages and link application details to their local READMEs.

**Tech Stack:** GitHub Markdown, Mermaid, PowerShell command examples, pytest documentation contract tests.

## Global Constraints

- Use only repository-relative links.
- Do not add generated image assets.
- Delivery claims must match `mvp.json` evidence levels.
- Preserve unrelated working-tree changes.

### Task 1: Documentation contract tests

**Files:** Modify `tests/repository/test_repository_layout.py`.

- [ ] Add assertions for three documentation pages, Mermaid diagrams, all nine application links, and the delivery-level legend.
- [ ] Run the focused test and observe failure against the current README.
- [ ] Commit only after the new documentation passes.

### Task 2: Visual root README

**Files:** Modify `README.md`.

- [ ] Add product heading, stable badges, navigation, a workflow diagram, an MVP topology diagram, five-minute start, application catalog, evidence legend, repository layout, safety rules, and documentation index.
- [ ] Keep application commands linked to application READMEs instead of duplicating every option.
- [ ] Run documentation contract tests.

### Task 3: Focused documentation pages

**Files:** Create `docs/ARCHITECTURE.md`, `docs/WORKFLOWS.md`, and `docs/CONTRIBUTING.md`; modify `docs/PROJECT_MAP.md`.

- [ ] Document ownership boundaries, public contracts, dependency direction, and artifact lifecycle.
- [ ] Document research, edit/localize, template/render, and publish workflows with Mermaid.
- [ ] Document application requirements, manifest fields, testing, evidence, language, secrets, and generated-artifact policy.
- [ ] Run all repository and capability tests, manifest validation, link-oriented tests, and `git diff --check`.
