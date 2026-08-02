# Client Contracts MVP

Client Contracts is the transport-neutral contract owner for the existing browser and future mobile or hosted clients. It exports one canonical bundle describing command envelopes, API routes, required scopes, compatibility and state ownership. It never reads Studio SQLite or owns workflow progress.

Delivery level: `DOMAIN_VERIFIED`. Deterministic export, exact replay, strict envelope validation and bounded client compatibility are verified locally.

```powershell
.\apps\client-contracts\run.ps1 export --output .\client-contracts.json --json
.\apps\client-contracts\run.ps1 check-client --client-version 1.2.0 --json
.\apps\client-contracts\run.ps1 validate-command --input .\create-run.json --expected-contract CMD-RUN-CREATE --json
```

Unknown fields are rejected. Version `1.x` clients at or above `1.0.0` are compatible with contract `1.0`; other majors are rejected until a declared contract revision exists. This decision does not authenticate the caller—Workspace Access owns admission.
