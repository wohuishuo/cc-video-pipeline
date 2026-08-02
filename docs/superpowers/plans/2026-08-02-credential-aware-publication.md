# Credential-aware Guarded Publication Plan

## Goal

Compose Guarded Publication, Credential Vault and Platform I/O through their public commands. Publication plans retain credential references only; the selected plaintext exists only inside Credential Vault and the one Platform I/O child environment.

## Contract

- Planning optionally maps one target platform to one bounded credential ID.
- Credential IDs affect plan/job fingerprints and appear as non-secret references in the immutable plan.
- Confirmed execution rejects referenced credentials when no vault boundary is configured.
- The adapter wraps Platform I/O with Credential Vault `run`; neither secret nor plaintext hash enters argv, plan, manifest or receipt.
- Platform I/O explicitly checks its named credential environment before launching an authenticated adapter.
- Serial checkpoint/replay behavior remains owned by Publication and unchanged.

## Implementation order

1. Add failing planning and adapter-composition tests.
2. Extend the additive planning contract and CLI flags.
3. Implement the public Vault-to-Platform-I/O command wrapper.
4. Run a real DPAPI-to-fake-platform child drill with redaction assertions.
5. Update publication, platform and architecture documentation.

## Non-goals

No real social upload, cookie-format migration, interactive login, credential renewal or hosted secret manager is proven in this slice.
