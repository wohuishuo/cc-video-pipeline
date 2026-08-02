# Resource Budget capability DAG

```mermaid
flowchart LR
    C["Configure budget"] --> R["Transactional reserve"]
    R --> G["Generation-bound renew/release"]
    R --> X["TTL reclamation"]
    S["Workspace Storage capacity fact"] -. "Policy" .-> C
    G -. "Fact" .-> A["Future Studio admission"]
```

| Node | Owner | Status | Dependency |
| --- | --- | --- | --- |
| Configure | Resource Budget | verified | SQLite durability, hard |
| Reserve | Resource Budget | verified | configured limit, hard |
| Renew/release | Resource Budget | verified | active lease generation, hard |
| TTL reclaim | Resource Budget | verified | UTC clock, hard |
| Storage capacity policy | Workspace Storage | adjacent integration verified | public CLI fact, substitute policy input |
| Studio admission | Video Graph Studio adapter | lowest unproven dependent node | Resource Budget public CLI |
