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
    C["G10 Complete Creator Catalog"] -->|Verified fact| S["G11 Exact Selection"]
    S -->|Command| P
    T["G12 Translation Provider Policy"] -->|Policy| P
    V["G13 Voice Provider Policy"] -->|Policy| P
    P -->|Verified local artifacts| O["G14 Local Delivery"]
    O -. Optional .-> U["G15 Publication Execution"]
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
| G10 | complete, non-truncated creator catalog | verified | Creator Discovery manifest | hard campaign gate |
| G11 | exact creator subset | verified | G10 Fact | hard campaign gate |
| G12 | explicit NLLB/DeepSeek translation policy | verified | provider readiness projection | substitutable provider |
| G13 | explicit Edge/Qwen3/original voice policy | verified | locale compatibility and provider readiness | substitutable provider |
| G14 | verified local MP4 delivery | verified contract/domain boundary | G03 and localization facts | hard completion boundary |
| G15 | authenticated private/draft upload receipt | unproven | Credential Vault, Publication and Platform I/O | optional platform gate |

The lowest unproven platform node is G15. It is optional and therefore does not block local campaign completion, but it blocks any claim that Studio completed a real authenticated upload.
