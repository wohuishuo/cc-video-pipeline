# Publication capability DAG

```mermaid
flowchart LR
    V["Verified video"] --> P["Build immutable plan"]
    M["Metadata JSON"] --> P
    T["Targets and accounts"] --> P
    R0["Credential references"] --> P
    P --> H["Plan SHA-256"]
    H --> C{"Exact confirmation?"}
    C -->|no| R["Reject without platform contact"]
    C -->|yes| G{"Visibility guaranteed?"}
    G -->|no| R
    G -->|yes| V0["Vault provider check + child injection"]
    V0 --> E["Serial Platform I/O execution"]
    E --> K["Per-target checkpoint"]
```

The planning node has no platform side effect and retains credential IDs only. The execution node never derives confirmation itself; Vault owns plaintext release and Platform I/O owns adapter execution.
