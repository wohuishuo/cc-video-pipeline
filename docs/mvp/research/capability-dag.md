# Research MVP Capability DAG

```text
DemoConnector
    |
    | Query: resolve / facts
    v
ResearchService + ResearchJob
    |
    | Command: collect
    v
DemoEvidenceCollector
    |
    | Fact: evidence committed
    v
ResearchDossier
    |
    | Fact: dossier committed
    v
FileResearchRepository
    |
    | Query: status / show
    v
JSON CLI result
```

| Dependency | Classification | Boundary preserved |
| --- | --- | --- |
| stable source specification | hard | identity and idempotency |
| `DemoConnector` | substitute | source query port without credentials |
| `DemoEvidenceCollector` | substitute | evidence adapter and committed locator |
| temporary/filesystem repository | hard adapter for this proof | lifecycle and atomic commit |
| real platform connectors | deferred substitute replacement | platform behavior not proven |
| FFmpeg and transcription engines | deferred substitute replacement | media evidence not proven |

The lowest node is proven through the independently runnable CLI. Dependent creator MVPs remain blocked until a real adjacent source/evidence integration is verified.
