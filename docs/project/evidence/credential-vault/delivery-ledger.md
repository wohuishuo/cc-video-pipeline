# Credential Vault Delivery Ledger

| Field | Record |
| --- | --- |
| Supported completion level | `DOMAIN_VERIFIED` |
| Evidence present | independent public CLI; CurrentUser DPAPI protect/unprotect; secret input by environment; ciphertext-only persistence; redacted lifecycle; context and provider isolation; explicit rotation/revocation; atomic replacement; child injection and exit propagation; guarded-publication composition |
| Evidence missing | hosted KMS; multi-process lock; ACL provisioning; backup/recovery; OAuth renewal; authenticated real-platform proof; production attack and operations evidence |
| Safe substitutes | local Windows account boundary; DPAPI optional entropy; one child process; credential references outside the vault |
| Decisions unapproved | remote secret store, identity binding, renewal policy, recovery policy, retention and audit sink |
| Forbidden claims | no hosted or production tenant custody; no automatic login; no immunity from same-user code; no multi-machine portability |

## Live Windows evidence

On 2026-08-02, the real launcher stored `youtube-main` with result `COMPLETED`, replayed the identical request as `DUPLICATE_COMPLETED`, described status `ACTIVE` without ciphertext, and released the recovered value into only the named environment of one Python child. The child exited `0`; the known plaintext was absent from the registry and all captured lifecycle output. The encrypted registry SHA-256 for that evidence run was `d305b81c11e1b618a19b785ae5668a0c44aae12fa2a4c604ffd0c38bdbdee44c`. The reproducible drill is `scripts/drills/credential-vault.ps1`.
