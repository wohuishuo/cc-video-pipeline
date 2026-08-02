# Video Graph Studio Capability DAG

```mermaid
flowchart LR
    G["G01 Graph Definition"] -->|Policy| R["G02 Workflow Run"]
    R -->|Fact| P["G03 Workflow Process"]
    P -->|Adapter| W["G04 Local Worker"]
    W -->|Fact| P
    P -->|Command| L["G05 Run Log"]
    R -->|Projection| D["G06 Dashboard"]
    L -->|Projection| D
    F["G07 Filesystem Browser"] -->|Query| D
    E["Existing Localization MVP"] -. Adapter .-> W
    P -->|Lease lifecycle| B["G09 Resource Budget"]
```

| Node | Result and owner | Status | Direct dependencies | Classification |
| --- | --- | --- | --- | --- |
| G01 | immutable validated graph | verified | none | hard |
| G02 | idempotent versioned run | verified | G01 Policy | hard |
| G03 | resumable ordered continuation | verified | G02 Fact | hard |
| G04 | one owned child process | verified | G03 Command | hard |
| G05 | append-only ordered log | verified | G02 identity | hard |
| G06 | read-only browser projection | verified | G02/G05 Projection | real loopback browser smoke |
| G07 | allowed-root folder evidence | verified | fixed configured roots | substitute: local filesystem only |
| G08 | real successful Edge media result | verified | external Edge service and localization MVP | named platform integration |
| G09 | reserve/renew/release local capacity | verified | Resource Budget public CLI | optional hard admission gate |
| G10 | authenticated private/draft upload receipt | unproven | Credential Vault, Publication and Platform I/O | hard platform gate |

The lowest unproven platform node is G10. It does not block domain verification of the control plane, but it blocks any claim that Studio completed a real authenticated upload.
