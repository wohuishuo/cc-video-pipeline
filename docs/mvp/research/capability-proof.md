# Research MVP Domain Core Capability Proof

| Field | Answer |
| --- | --- |
| Result | A demo source produces one committed, inspectable research dossier without network or model dependencies. |
| Owner | `ResearchJob` owns lifecycle; `ResearchDossier` owns committed dossier versions; `FileResearchRepository` is their persistence adapter. |
| Invariants | Stable source/config identity, idempotent duplicate create, conflict rejection, explicit terminal gaps, resumable failure, atomic dossier commit, credential exclusion, workspace confinement. |
| Public contract | `create`, `status`, `show`, `retry`; `SourceConnector` query port; `EvidenceCollector` adapter port; committed dossier fact. |
| Hard closure | Normalized `SourceRef`, research lifecycle, committed evidence, dossier commit. |
| Substitutes | Fixed demo source connector, demo evidence collector, temporary filesystem workspace. |
| Decision gates | Real Bilibili/YouTube authentication and evidence policies are not selected in this proof. |
| Non-goals | Network access, cookies, FFmpeg, transcription models, post-publication analytics, production verification. |

## RED contract

The first assertion requires equivalent normalized source/configuration input to produce a stable job ID. It must fail because the research domain package does not exist before implementation.

## Failure matrix

| Case | Required behavior |
| --- | --- |
| Duplicate | Return the existing dossier without committing a second version. |
| Conflict | Reject the same job identity with different canonical state. |
| Stale | Evidence-affecting configuration produces a different job identity. |
| Reentry | Completed create and retry return the committed dossier. |
| Partial failure | Persist `failed`, keep dossier absent, allow retry. |
| Cleanup | Temporary workspaces are removed; atomic writes leave no temporary file. |

## Evidence receipt

- RED evidence: missing domain, repository, service, and CLI entry modules each failed before implementation.
- GREEN evidence: 12 focused tests passed; the CLI subprocess produced a committed `complete_with_gaps` dossier.
- Owner contract: `ResearchService` owns lifecycle and `FileResearchRepository` commits job/dossier state.
- Substitutes: demo connector, demo collector, generated transcript, temporary filesystem.
- Missing evidence: real source connectors, authentication, FFmpeg, transcription, crash recovery, concurrency, scale.
- Supported level: `DOMAIN_VERIFIED`.
- Forbidden claims: platform integration, production verification, legacy replacement, real analytics, solved login.
