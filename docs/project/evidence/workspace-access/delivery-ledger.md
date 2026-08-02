# Workspace Access Delivery Ledger

| Field | Record |
| --- | --- |
| Supported completion level | `DOMAIN_VERIFIED` |
| Evidence present | independent launcher and manifest; canonical workspace roots; initialization replay/conflict; 256-bit random credentials; digest-only persistence; explicit scopes; environment-only verification input; expiry; revocation; redacted decisions; atomic registry replacement; real CLI lifecycle |
| Evidence missing | Studio HTTP composition; hosted identity provider; tenant-scoped run/artifact storage; OS ACL hardening; multi-process registry lock; remote vault; security/attack review; audit export |
| Safe substitutes | local JSON registry; short-lived bearer credential; loopback-only Studio remains unauthenticated |
| Decisions unapproved | IdP, roles, refresh flow, device enrollment, vault, tenant model, recovery, retention and compliance policy |
| Forbidden claims | no production authentication; no secure remote access; no tenant isolation; no OAuth/MFA; no compliance certification |

## Live CLI evidence

On 2026-08-02, registry initialization returned `COMPLETED`; credential `0fd3da96b27bc5cb` was issued with `runs:read,runs:write`; the plaintext was absent from the persisted registry; `runs:write` returned `AUTHORIZED`; revocation returned `COMPLETED`; and the same credential then returned `REJECTED_UNAUTHORIZED`. Final redacted registry SHA-256: `80f57e66bf67690efbf0d5a9ecb7a2489f4c9aa61f5d18dc1704a0fa8adc6f65`.
