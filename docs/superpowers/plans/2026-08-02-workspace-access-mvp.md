# Workspace Access MVP Implementation Plan

## Goal

Create an independently runnable owner for workspace identity and least-privilege bearer credentials. Keep it separate from Graph Studio so desktop, hosted and mobile admission adapters can reuse the same policy without owning media or workflow state.

## Contract

- Registry owns workspace IDs, canonical allowed roots, credential metadata, expiry and revocation.
- Plaintext tokens are returned once and never persisted.
- Authorization consumes a token from an environment variable and returns a redacted decision.
- Known scopes are explicit; no UI or Graph node can grant itself authority.
- Registry updates publish atomically and advance a revision.

## Implementation order

1. Write domain tests for initialization replay/conflict and canonical roots.
2. Write credential tests for entropy, hashing, scope, expiry, revocation and redaction.
3. Implement JSON contracts and atomic registry owner using the Python standard library.
4. Add a PowerShell launcher, doctor command, manifest and independent documentation/evidence.
5. Run CLI smoke evidence and repository regression.

## Non-goals

No hosted identity provider, password login, OAuth, billing, remote secret vault, LAN binding or Studio integration in this independent slice.
