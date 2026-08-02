# Credential Vault capability evidence

- Domain tests prove exact put replay, changed-input conflict and explicit rotation.
- Tests prove public lifecycle results omit both ciphertext and plaintext.
- Revocation destroys the ciphertext field and blocks later resolution.
- Context binding rejects ciphertext copied from one credential record to another.
- Registry writes use a same-directory temporary file, flush, `fsync` and atomic replacement.
- CLI tests prove env-only intake, missing-variable rejection, child-only target injection and child exit-code propagation.
- Provider tests reject releasing a stored credential to a different platform adapter.
- A real Windows launcher drill used CurrentUser DPAPI, repeated the write, described redacted metadata and injected the recovered secret into one Python child without plaintext appearing in persisted or captured output.
- A real Guarded Publication drill composed a credential reference through provider verification into one Platform I/O child.

No hosted secret manager, OS ACL provisioning, multi-process lock, backup/restore, browser credential capture, automatic renewal or production security review evidence is present.
