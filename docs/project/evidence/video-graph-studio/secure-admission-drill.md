# Secure Workspace Admission Drill

Date: 2026-08-02
Environment: Windows 11, loopback `127.0.0.1:8774`, real Workspace Access CLI, real Video Graph Studio HTTP server

## Boundary under test

One Studio process and data root were bound to workspace `secure-local`. Studio obtained canonical allowed roots only through `apps/workspace-access/run.ps1 describe` and obtained every authorization decision through `run.ps1 authorize`. No Workspace Access private module was imported.

## Observed results

| Probe | Result |
| --- | --- |
| Public health | HTTP `200`; `accessRequired=true`; workspace `secure-local` |
| Missing bearer | HTTP `401` |
| Correct bearer, wrong workspace | HTTP `403` |
| Reader credential, run query | HTTP `200` |
| Reader credential, run creation | HTTP `403` |
| Writer credential with `artifacts:read`, folder query | HTTP `200` |
| Writer credential, run creation | HTTP `201`; run `secure-live-create` committed as `CREATED` |
| Browser bootstrap fragment | removed from the visible URL; UI settled on `Access denied` for a dummy credential |
| Persisted secrets | neither plaintext credential occurred in the registry |

Credential IDs were `a7c5c42c1e8ace33` and `4247bdfcfc151a28`; only IDs, digests, scopes and lifecycle timestamps were persisted. The secure server was then stopped and port `8774` was confirmed closed.

## What this proves

- Route-specific local admission happens before Run application mutation.
- Workspace roots come from the independent policy owner instead of browser input.
- The plaintext bearer travels to the policy process through an environment variable, not argv.
- The browser can load public assets, learn that access is required and keep credentials session-scoped.

## What this does not prove

This is not hosted authentication, tenant isolation, OAuth/MFA, remote secret custody, an attack review, LAN safety or production security. A secure process serves one configured workspace and one local data root.
