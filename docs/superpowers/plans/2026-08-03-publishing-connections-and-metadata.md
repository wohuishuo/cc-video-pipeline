# Publishing Connections and Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. The user has prohibited subagents, so execution is inline.

**Goal:** Preserve source publishing metadata, produce editable translated release metadata, and allow publication only through an explicitly connected account with an honest private/public capability policy.

**Architecture:** Source Intake owns downloaded metadata and thumbnail facts. A new Release Metadata MVP consumes source facts plus translated/localized facts and writes editable per-language metadata. Credential Vault owns secrets; a redacted Connection Catalog projects account readiness. Existing Publication planning and execution remain the only owners of upload intent and side effects.

**Tech Stack:** Python 3.12, yt-dlp info JSON and thumbnails, DPAPI Credential Vault, existing Publication and platform adapters, native Studio web UI.

## Global Constraints

- Never expose cookie, OAuth or API-key plaintext through HTTP responses, logs, argv or manifests.
- No destination can be selected as executable without an active connection and an installed execution adapter.
- Local-only completion remains valid.
- Visibility is explicit per destination and part of the publication fingerprint.
- Plan-only platforms may save metadata and plans but cannot report upload success.
- No subagents.

---

### Task 1: Source publishing metadata

**Files:** `video_platform/download.py`, `apps/source-intake/intake/platform_adapter.py`, `apps/source-intake/intake/contracts.py`, matching tests.

- [ ] Write failing tests for title, description, hashtag tags, source URL, thumbnail path and info JSON hash.
- [ ] Add `--write-thumbnail` and normalize the yt-dlp info document into bounded receipt facts.
- [ ] Publish file-backed thumbnail and info facts in Source Manifest with hashes.
- [ ] Verify stale metadata or thumbnails reject replay.

### Task 2: Independent Release Metadata MVP

**Files:** create `apps/release-metadata/`, `tests/release_metadata_mvp/`, and MVP evidence docs.

- [ ] Define a command consuming Creator item, Source Manifest, Translation Manifest and Localization Manifest.
- [ ] Write failing tests for exact derivative/language coverage and editable title, description, tags and thumbnail outputs.
- [ ] Implement deterministic source metadata normalization and provider-selected title/description translation.
- [ ] Preserve source and translated metadata side by side with hashes and review status.
- [ ] Verify duplicate, conflict, stale thumbnail, partial translation and cleanup behavior.

### Task 3: Redacted Connection Catalog

**Files:** modify Credential Vault with `list`, create Studio platform connection service, API routes and tests.

- [ ] Write failing tests that list active/revoked records without ciphertext.
- [ ] Add generic credential setup for cookie/OAuth material through request-body to DPAPI custody.
- [ ] Project installed adapter, connection state, supported visibility and evidence level for each platform.
- [ ] Add headed-login Graph commands only for installed browser adapters.

### Task 4: Publication composition and UI

**Files:** Studio API/graphs/adapters, Creator workspace model/UI, publication contract tests.

- [ ] Write failing readiness tests: disconnected account blocks execution, plan-only remains local, local-only remains ready.
- [ ] Replace free-form account labels with Connection Catalog selections.
- [ ] Add per-language metadata review, thumbnail preview and private/public selector.
- [ ] Compose confirmed plans only after localization and release metadata facts commit.
- [ ] Execute only verified platform/visibility pairs and show external IDs or fenced errors.

### Task 5: Live evidence and delivery audit

- [ ] Run a local plan for every configured platform.
- [ ] Perform authenticated upload only when the user account connection is active and the exact side effect is explicitly confirmed.
- [ ] Record real external IDs, visibility and thumbnail behavior separately per platform.
- [ ] Keep unsupported platforms at `DOMAIN_VERIFIED` or plan-only and document the missing evidence.
