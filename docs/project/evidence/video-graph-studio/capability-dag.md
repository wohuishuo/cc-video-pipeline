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
| G08 | real successful Edge media result | unproven | external Edge service and localization MVP | hard platform gate |

The lowest unproven platform node is G08. It does not block domain verification of the control plane, but it blocks a claim that a real localized output completed through the website.
