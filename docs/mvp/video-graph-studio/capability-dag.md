# Video Graph Studio Capability DAG

```mermaid
flowchart LR
    Graph -->|Policy| Run
    Run -->|Fact| Process
    Process -->|Adapter| Worker
    Worker -->|Fact| Process
    Run -->|Projection| Dashboard
    Log -->|Projection| Dashboard
```

Graph, Run, Process, Worker, Log, Folder Browser and Dashboard contracts are verified. Real successful Edge localization through the graph is the lowest unproven platform node. See the [full DAG](../../project/evidence/video-graph-studio/capability-dag.md).

