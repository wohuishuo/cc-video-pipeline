# Creator MVP Vertical-Slice Refactor Design

## Goal

Replace the repository's tool-shaped architecture with a small set of creator-outcome MVPs. A capability is an MVP only when a creator can run it independently and receive a useful finished result.

Existing scripts are behavioral evidence and possible migration sources. Their folders, command boundaries, and implementation steps do not define the new architecture.

## Boundary Rule

A unit is an independent MVP only if all of these are true:

1. It produces a result useful to the creator without requiring the next MVP.
2. It can be demonstrated with one public input and one finished output package.
3. It has lifecycle or mutable state that must be owned independently.
4. It can fail, be retried, and be verified without running unrelated creator workflows.

Technical steps such as scene detection, loudness analysis, frame extraction, path resolution, authentication, FFmpeg invocation, and model routing fail this test. They remain private operations or adapters inside an outcome MVP.

## Creator Outcomes

The target system has six possible MVPs. Only the first is in the initial implementation scope.

| MVP | Creator input | Independently useful result | State owned |
| --- | --- | --- | --- |
| `research-mvp` | video URL, channel, or topic | research dossier with source facts, transcript, visual evidence, patterns, and reusable observations | research job and dossier version |
| `authoring-mvp` | idea and optional research dossier | approved content package: brief, titles, script, storyboard, asset list | content-package revisions and approval state |
| `voice-mvp` | approved script and voice policy | narration package with audio, timing, pronunciation notes, and engine record | voice run and narration version |
| `production-mvp` | approved content package, narration, and assets | watchable horizontal master video | production job and master version |
| `distribution-mvp` | approved master and platform targets | platform-ready exports, subtitles, cover, title, and publishing checklist | distribution package version |
| `review-mvp` | published-video identifiers and snapshots | performance review with evidence-backed recommendations | metric snapshots and review version |

`review-mvp` is deferred until the repository has a real workflow that tracks the user's published videos over time. Generic Bilibili lookup does not justify a separate analytics MVP.

Cos dance, Vlog, and knowledge videos are policies/templates applied to these MVPs, not separate state owners.

## Authentication and Platform Data

Login is not an MVP. Cookies, browser sessions, API tokens, and anonymous access are authentication strategies behind source connectors.

For Bilibili:

- video metadata, search results, transcripts, comments, and public channel data used to understand a topic belong to `research-mvp`;
- credentials are supplied to a `BilibiliConnector` adapter and never become research-domain state;
- post-publication metric snapshots for the creator's own released videos belong to `review-mvp` only when that workflow is implemented;
- connector code may be shared, but shared code does not merge the research dossier owner with the review owner.

YouTube and local files use equivalent connectors. The research domain consumes normalized source facts rather than platform-specific private objects.

## Initial Vertical-Slice Brief: Research MVP

### Observable result

Given a supported video URL, produce a versioned research dossier that a creator can use immediately for topic selection, script writing, or visual planning.

The dossier contains:

- source identity and metadata;
- transcript or an explicit transcript-unavailable fact;
- representative visual evidence;
- structural timeline and content sections;
- reusable hooks, patterns, and cautions;
- provenance for every machine-derived artifact;
- a completion summary that distinguishes missing evidence from failed processing.

Raw scene scores, loudness samples, downloaded media, and extracted frames are evidence behind the dossier. They are not separate MVP outputs or independent public products.

### Commands and queries

- `research create <source>` creates or resumes a research job.
- `research status <job>` reports lifecycle and missing evidence.
- `research show <job>` returns the committed dossier manifest.
- `research retry <job>` retries failed private operations without invalidating committed evidence.

### State-owner matrix

| Mutable state | Unique owner | Protected invariant | Public mutation | Public read/fact |
| --- | --- | --- | --- | --- |
| research job lifecycle | `ResearchJob` | one source and configuration identify one job version; retry never converts partial evidence into committed evidence | create/retry job | job advanced/failed/completed |
| research dossier version | `ResearchDossier` | a committed dossier identifies its source, evidence, schema, and missing items | commit dossier | dossier committed |
| source credentials | connector adapter, outside the domain | secrets never appear in dossier, logs, or manifests | adapter configuration | authenticated/anonymous connection result |
| cached raw media and derived evidence | `ResearchWorkspace` internal to `research-mvp` | paths remain inside the job workspace; temporary artifacts are not committed evidence | stage/promote evidence | evidence staged/committed |

The research coordinator owns job continuation only. Scene detection, loudness processing, extraction, transcription, and source lookup do not own independent business lifecycle state.

### Invariants

- A dossier cannot be committed without a stable source identity.
- Missing optional evidence is recorded explicitly and cannot masquerade as success.
- Retrying a failed operation preserves already committed evidence.
- Changing source identity or evidence-affecting configuration creates a new dossier version.
- Credentials and platform session material never appear in committed outputs.
- A connector failure is distinguishable from an unsupported source and from unavailable content.
- All committed filesystem paths remain under the selected research workspace.

### Non-goals

- No independent scene-analysis, loudness-analysis, or frame-extraction product.
- No generic workflow engine.
- No standalone workspace/path service.
- No separate login service.
- No database, queue, GUI, or cloud deployment.
- No attempt to preserve every legacy command or directory.
- No large-model or network dependency in domain tests.
- No post-publication analytics in the first slice.

## Typed Relationships

Relationships inside `research-mvp` are ports and private policies, not public MVP boundaries.

| Provider | Relationship | Consumer | Classification | Invariant protected |
| --- | --- | --- | --- | --- |
| source connector | `Query: resolve_source` | research job | hard | stable source identity |
| source connector | `Query: fetch_source_facts` | dossier builder | substitute-capable | normalized provenance |
| authentication strategy | `Strategy` | source connector | substitute | secrets stay outside domain state |
| media acquisition adapter | `Adapter` | evidence collector | substitute | raw media validation |
| transcription adapter | `Adapter` | evidence collector | substitute | transcript provenance |
| visual evidence policy | `Policy` | evidence collector | substitute | bounded representative evidence |
| signal extraction adapter | `Adapter` | visual evidence policy | optional substitute | assists selection but owns no state |
| evidence collector | `Fact: EvidenceCommitted` | dossier builder | hard | only promoted evidence is published |
| dossier builder | `Fact: DossierCommitted` | research job | hard | completion follows committed result |

Fake connectors and generated local media preserve the boundaries for domain verification. Real Bilibili, YouTube, yt-dlp, FFmpeg, and transcription engines are platform-integration evidence, not prerequisites for proving the domain lifecycle.

## Capability DAG

```text
Fixed source specification or fake connector
        |
        | Query: normalized source identity/facts
        v
Research job lifecycle
        |
        | Command: collect evidence
        v
Evidence collection with substitutable adapters
        |
        | Fact: committed evidence
        v
Research dossier builder
        |
        | Fact: committed dossier
        v
Observable research package
```

The lowest unproven node is normalized source resolution within the research slice, not a reusable infrastructure product. The first test proves that one source becomes one stable research job without leaking connector credentials or filesystem assumptions.

## Research Package Contract

```json
{
  "schema_version": "1",
  "job_id": "stable-id",
  "status": "complete_with_gaps",
  "source": {
    "platform": "bilibili",
    "source_id": "BV...",
    "canonical_url": "https://..."
  },
  "facts": {},
  "evidence": [],
  "timeline": [],
  "patterns": [],
  "gaps": [],
  "provenance": []
}
```

Allowed terminal statuses are `complete`, `complete_with_gaps`, and `failed`. `complete_with_gaps` is useful delivery with named missing optional evidence; it is not a hidden failure.

## Implementation Direction

Build the research MVP as a new vertical slice with clean contracts. Do not first reorganize legacy files.

1. Prove normalized source resolution and research-job identity using a fake connector.
2. Prove lifecycle, retry, conflict, stale-version, partial-failure, and cleanup behavior with an in-memory or temporary workspace.
3. Prove dossier commit from fake evidence.
4. Add one local-file connector and generated media fixture as the first real adjacent integration.
5. Add FFmpeg-derived evidence behind the private evidence collector.
6. Add transcription behind the same private boundary.
7. Add Bilibili/YouTube connectors and credential strategies.
8. Compare useful legacy behavior against the new result and selectively port algorithms or command options.
9. Retire legacy entry points only after the research MVP demonstrates equivalent or better creator-visible behavior.

Legacy code is never imported merely to reduce migration effort. It is reused only when a focused test shows that the behavior belongs inside the new contract.

## Test and Evidence Strategy

For each capability increment record:

- public contract and owner;
- RED assertion and observed failure;
- focused contract tests;
- adjacent integration using the previous real increment;
- duplicate, conflict, stale, reentry, partial-failure, and cleanup behavior;
- exact commands and results;
- explicit non-goals.

Normal tests use fake connectors, fake adapters, generated text, and short generated media. Separate platform checks cover real FFmpeg, real network sources, cookies, and locally installed transcription models.

## Later Composition

Only committed packages cross MVP boundaries:

```text
research dossier ──Query──> authoring-mvp
approved content package ──Query──> voice-mvp
approved content + narration ──Query──> production-mvp
approved master ──Query──> distribution-mvp
published identifiers ──Query──> review-mvp
```

Downstream MVPs cannot mutate upstream packages. A new upstream version triggers an explicit downstream revision rather than silently overwriting work.

## Delivery Ledger

- Supported completion level: `DESIGNED`.
- Evidence present: repository inventory, creator-outcome boundaries, unique state owners, typed research relationships, dependency order, contract sketch, migration rules.
- Evidence missing: RED tests, implemented research contracts, lifecycle tests, adjacent integration, real connector checks, model checks.
- Substitutes planned: fake source connector, fake authentication strategy, fake evidence adapters, temporary research workspace, generated media.
- Decisions still unapproved: exact authoring approval policy and long-term review metric schedule; neither blocks `research-mvp`.
- Claims forbidden: research MVP implemented; legacy pipeline replaced; Bilibili login solved; analytics verified; end-to-end video production ready; production verification achieved.

