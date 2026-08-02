# Video Graph Studio Capability DAG

```mermaid
flowchart LR
    Graph -->|Policy| Run
    Run -->|Fact| Process
    Process -->|Adapter| Worker
    Process -->|Lease lifecycle| Budget[Resource Budget]
    Worker -->|Fact| Process
    Run -->|Projection| Dashboard
    Log -->|Projection| Dashboard
```

Graph, Run, Queue, Process, Worker, Log, Folder Browser, Dashboard and optional Resource Budget composition are verified. Real authenticated private/draft upload remains the lowest unproven platform node. See the [full DAG](../../project/evidence/video-graph-studio/capability-dag.md).
