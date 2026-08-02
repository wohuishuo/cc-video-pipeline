# Video Graph Studio Capability DAG

```mermaid
flowchart LR
    Catalog[Workflow Catalog] -->|Projection| Builder[Guided Graph Builder]
    Contracts[Client Contracts] -->|Preflight| Builder
    Health[Studio Health] -->|Preflight| Builder
    Builder -->|Versioned command| Graph
    Graph -->|Policy| Run
    Run -->|Fact| Process
    Process -->|Adapter| Worker
    Process -->|Lease lifecycle| Budget[Resource Budget]
    Worker -->|Fact| Process
    Run -->|Projection| Dashboard
    Log -->|Projection| Dashboard
    Graph -->|Contains| SourceLoop[Source Loop]
    Graph -->|Contains| AsrLoop[Transcription Loop]
    Graph -->|Contains| TranslationLoop[Translation Loop]
    Graph -->|Contains| VoiceLoop[Voice Loop]
    Graph -->|Contains| LocalizationLoop[Localization Loop]
```

Workflow Catalog, guided Draft Graph projection, independent readiness checks, exact node/Loop rendering, Graph, Run, Queue, Process, Worker, Log, Folder Browser, Dashboard and optional Resource Budget composition are verified. The builder only selects admitted fixed Graphs; arbitrary node insertion and edge editing are deliberately absent. Real authenticated private/draft upload remains the lowest unproven platform node. See the [full DAG](../../project/evidence/video-graph-studio/capability-dag.md).
