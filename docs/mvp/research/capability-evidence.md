# Research MVP Capability Evidence

## Public contract and owner

- CLI: `python -m research_mvp --workspace PATH create|status|show|retry`.
- Source query port: `SourceConnector.resolve` and `SourceConnector.facts`.
- Evidence adapter port: `EvidenceCollector.collect`.
- Lifecycle owner: `ResearchService` operating on `ResearchJob`.
- Persistence owner: `FileResearchRepository` atomically commits job and dossier JSON.

## RED observations

| Increment | Command | Observed failure |
| --- | --- | --- |
| source identity | `python -m unittest tests.research_mvp.test_models -v` | `No module named 'research_mvp'` |
| repository | `python -m unittest tests.research_mvp.test_repository -v` | `No module named 'research_mvp.repository'` |
| lifecycle | `python -m unittest tests.research_mvp.test_service -v` | `No module named 'research_mvp.service'` |
| CLI | `python -m unittest tests.research_mvp.test_cli -v` | package had no `research_mvp.__main__` |

Each failure occurred before the corresponding production module existed.

## GREEN observations

| Increment | Result |
| --- | --- |
| domain values | 3 tests passed |
| repository plus domain | 7 tests passed |
| lifecycle suite | 11 tests passed |
| CLI plus full suite | 12 tests passed |

The independent demonstration produced dossier job `507a33309bf66c9c2c89` with status `complete_with_gaps`, demo transcript evidence, SHA-256 provenance, and `visual_evidence_unavailable` in `gaps`.

## Failure matrix

| Case | Executable evidence |
| --- | --- |
| duplicate | same source/config returns dossier version 1 |
| conflict | same repository job ID with different canonical state raises `ConflictError` |
| stale | changed evidence configuration produces a different stable job ID |
| reentry | completed create returns the committed dossier |
| partial failure | collector error stores `failed`; retry commits the same job ID |
| cleanup | every test temporary workspace is removed by `TemporaryDirectory` teardown; atomic writes use `os.replace` |

## Substitutes and limits

- `DemoConnector` proves the normalized query seam; it does not prove Bilibili, YouTube, redirects, deleted media, or authentication.
- `DemoEvidenceCollector` proves the evidence port, provenance record, and explicit gaps; it does not prove media download, transcript quality, visual selection, or model execution.
- Filesystem tests prove process-local atomic replacement and reload; they do not prove concurrent multi-process locking, backup, or crash recovery across every filesystem.

## Non-goals

No platform integration, legacy migration, analytics, real login, real media evidence, or production-readiness claim is supported by this evidence.
