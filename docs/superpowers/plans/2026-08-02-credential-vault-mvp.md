# Credential Vault MVP Plan

## Goal

Create an independently runnable Windows-first owner for local credential custody. It protects provider secrets with CurrentUser DPAPI and releases one secret only into one explicitly launched child-process environment. It must not own platform login semantics, publication runs, workspace admission or workflow state.

## Contract

- Accept secret material only from a named environment variable at the public CLI boundary.
- Persist DPAPI-protected ciphertext and non-secret metadata; never persist plaintext or a plaintext digest.
- Repeating an identical put replays; changed input conflicts until an explicit rotation is requested.
- Describe is redacted, rotation is explicit and revocation destroys the stored ciphertext.
- Run decrypts only for the selected record, injects it into a named child environment variable, uses an argv array without a shell and returns the child exit code.
- Registry changes use same-directory atomic replacement.

## Implementation order

1. Add failing domain tests with a deterministic fake cipher.
2. Add failing CLI tests for env-only intake and redacted output.
3. Implement registry, DPAPI adapter and public launcher.
4. Add the independent MVP manifest, README and four evidence artifacts.
5. Run a real Windows DPAPI round-trip and child-injection drill.
6. Update repository, architecture, capability and operations indexes.

## Non-goals

No browser-cookie extraction, OAuth refresh, hosted key management, shared-machine secrets, platform publication, remote tenant isolation or automatic credential renewal is implemented in this slice.
