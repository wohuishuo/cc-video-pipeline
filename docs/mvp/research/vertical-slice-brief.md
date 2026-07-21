# Research MVP Vertical Slice Brief

## Observable result

Given `demo:<id>`, one command creates or resumes a stable research job and returns a committed JSON research dossier. The result is useful as a contract demonstration and explicitly names unavailable visual evidence.

## Use cases

- `create`: resolve a source, collect evidence, and commit a dossier.
- `status`: query lifecycle state without mutation.
- `show`: query the committed dossier.
- `retry`: resume a failed job or return a completed result idempotently.

## State owners

| State | Unique owner |
| --- | --- |
| job lifecycle | `ResearchJob` through `ResearchService` |
| committed dossier versions | `ResearchDossier` through `FileResearchRepository` |
| demo transcript fixture | `DemoEvidenceCollector` inside the selected evidence workspace |

## Protected invariants

- Normalized source plus evidence-affecting configuration produces a stable job ID.
- Duplicate create does not repeat dossier commit.
- Conflicting canonical state is rejected.
- Partial failure is recorded as `failed` and remains retryable.
- Optional missing evidence is named by `complete_with_gaps`.
- Canonical URLs cannot contain user-info credentials.
- Job IDs cannot escape the selected workspace.
- JSON state and dossier versions are atomically promoted.

## Decision gates

- Real Bilibili/YouTube source normalization is not selected.
- Cookie, browser-session, and anonymous authentication strategies are not selected.
- Real transcript and visual evidence policies are not selected.

## Non-goals

- No network access, cookies, FFmpeg, or transcription models.
- No scene-analysis, frame-extraction, login, or workspace MVP.
- No claim that legacy reference analysis has been replaced.
- No platform or production verification.
