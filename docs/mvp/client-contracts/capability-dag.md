# Client Contracts capability DAG

```mermaid
flowchart LR
    D["Canonical contract definition"] --> E["Atomic bundle export / show"]
    D --> V["Command envelope validation"]
    D --> C["Client compatibility decision"]
    E --> HTTP["Studio public HTTP discovery"]
    HTTP --> B["Desktop browser"]
    E --> M["Future mobile client"]
    E --> H["Future hosted client"]
```

Clients retain disposable projections. Video Graph Studio remains the authoritative run-state writer; the HTTP adapter only projects the Client Contracts owner's immutable result.
