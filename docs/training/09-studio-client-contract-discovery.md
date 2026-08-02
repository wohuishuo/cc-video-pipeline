# Studio client-contract discovery tutorial

Client Contracts is the transport-neutral owner for desktop, future mobile and future hosted clients. Studio exposes that owner's exact public result; it does not maintain a second schema.

## Inspect the owner directly

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File apps/client-contracts/run.ps1 show --json
```

The result contains the bundle and SHA-256. The bundle names command envelopes, endpoints, required scopes, compatibility and state owners.

## Inspect Studio discovery

Start Studio, then request:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/v1/contracts
```

No bearer credential or workspace header is required. Discovery exposes interface metadata only—never run state, roots or secrets. The result is cached for one server generation so a client cannot observe a changing contract mid-session.

## Browser behavior

The desktop UI requests discovery before health and before enabling **Run graph**. It requires Create, Start and Cancel declarations, verifies the discovery endpoint exists, and fills every envelope's `contractVersion` from the bundle. A malformed/unavailable bundle leaves mutation disabled and shows `Contract unavailable`.

## Reproduce the real proof

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/drills/studio-contract-discovery.ps1
```

The drill uses an admission adapter that throws if called, proving contract discovery occurs before authentication. This validates the local HTTP composition, not a mobile app or hosted service.
