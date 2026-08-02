# Video Automation System Component Map

Every mutable artifact family has one authoritative writer. Coordinators own continuation, not media-domain truth.

```mermaid
flowchart TB
    Client["Browser / future mobile client"] -->|"credential + versioned command"| Admission["Admission adapter"]
    Access["Workspace Access"] -->|"redacted scope decision"| Admission
    Storage["Workspace Storage"] -->|"state/artifact namespace"| Router["Workspace Runtime Router"]
    Vault["Credential Vault"] -->|"one child environment"| Publish["Platform I/O"]
    Admission -->|"multi workspace"| Router
    Router --> HTTP
    Admission -->|"fixed workspace"| HTTP["HTTP transport adapter"]
    HTTP --> Run["Workflow Run Owner"]
    Run --> Queue["Durable Start Queue"]
    Queue --> Process["Graph Process Manager"]
    Process -->|public command| Intake["Source Intake"]
    Process -->|public command| Transcript["Transcription"]
    Process -->|public command| Translation["Translation"]
    Process -->|public command| Voice["Voice Rendering"]
    Process -->|public command| Compose["Video Composition"]
    Process -->|public command| Publish["Platform I/O"]
    Intake -->|committed fact| Process
    Transcript -->|committed fact| Process
    Translation -->|committed fact| Process
    Voice -->|committed fact| Process
    Compose -->|committed fact| Process
    Publish -->|committed fact| Process
    Run --> Projection["Disposable dashboard projection"]
    Projection --> Client
```

## State owners

| Mutable state | One authoritative writer | Readers |
| --- | --- | --- |
| Graph revision/fingerprint | Graph Definition | Run admission, browser projection |
| Workspace identity/credential lifecycle | Workspace Access | admission adapters, operators |
| Workspace state/artifact/temp namespace and capacity projection | Workspace Storage | Workspace Runtime Router, operators |
| Client command/endpoint compatibility bundle | Client Contracts | browser, future mobile and hosted clients |
| Run lifecycle/version | Workflow Run Owner | Process, dashboard |
| Start-request order/claim | Durable Start Queue | Process, dashboard |
| Step checkpoint/continuation | Workflow Process Manager | Run projection, recovery |
| Source manifest/receipt | Source Intake | downstream adapters, verification |
| Transcript artifact/receipt | Transcription | translation, editor, dashboard |
| Translation artifact/receipt | Translation | voice, subtitle, editor |
| Voice clips/receipt | Voice Rendering | audio composition |
| Localized video/receipt | Video Composition | publication, preview |
| Upload plan/receipt | Platform I/O | dashboard, operator |
| Encrypted local platform secrets and lifecycle | Credential Vault | selected child platform adapter only |
| Platform interpretation of cookies/tokens | Credential/Profile Adapter | owning platform adapter only |

## Replaceable client boundary

```mermaid
flowchart LR
    Desktop["Desktop browser"] --> Contracts["Command / Query contracts v1"]
    Mobile["Future mobile app"] --> Contracts
    Hosted["Future hosted console"] --> Contracts
    Owner["Client Contracts"] --> Contracts
    Contracts --> Admission["Authentication + admission adapter"]
    Admission --> Runs["Same Run and Process owners"]
```

Desktop defaults to anonymous loopback admission. Optional fixed secure mode binds one process to one workspace. Optional multi-workspace mode composes Workspace Access and Workspace Storage through public CLIs, authorizes the header workspace and lazily creates isolated state/artifact runtimes. All runtime engines share one process-wide execution gate. Guarded Publication now passes credential references through Credential Vault's provider-bound public child boundary into Platform I/O; real authenticated platform proof remains pending. Commercial hosting still needs a real identity provider, remote secret custody, hard resource reservations and production security evidence; it must not move workflow truth into the UI.

## Cross-boundary rules

- A program may import shared schemas, not another program's private implementation.
- A command requests work; a committed fact proves inspectable completion.
- Projections are disposable and cannot authorize media mutation.
- Platform callbacks enter through a typed adapter and cannot call another owner directly.
- Unknown partial external outcomes become failed or quarantined evidence, never inferred success.
