# Workspace Access capability evidence

- Domain tests prove workspace initialization replay and changed-identity conflict.
- Domain tests prove canonical existing roots, fixed known scopes and bounded identifiers.
- Credential tests prove plaintext is returned once and absent from the persisted registry.
- Authorization tests prove digest comparison, scope enforcement, workspace isolation, expiry and revocation.
- CLI tests prove secret input comes from an environment variable and authorization output is redacted.
- Registry writes use a same-directory temporary file, flush, `fsync` and atomic replacement.

No external identity provider, Windows ACL policy, hosted tenant isolation, security audit or production attack evidence is present.
