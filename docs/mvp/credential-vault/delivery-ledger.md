# Credential Vault delivery ledger

| Field | Record |
| --- | --- |
| Supported completion level | `DOMAIN_VERIFIED` |
| Evidence present | independent launcher; env-only intake; CurrentUser DPAPI; contextual binding; replay/conflict; explicit rotation/revocation; ciphertext destruction; redacted results; atomic registry; child argv execution; real Windows drill |
| Evidence missing | multi-process locking; ACL provisioning; hosted KMS; remote identity binding; renewal; backup/restore; production attack review and load evidence |
| Substitutes | local Windows user trust boundary; atomic JSON; short-lived child environment |
| Decisions unapproved | hosted secret vendor, key rotation, recovery, credential renewal, organization policy and regional placement |
| Forbidden claims | no production tenant custody; no protection from code already executing as the same user; no remote portability; no automatic platform login |
