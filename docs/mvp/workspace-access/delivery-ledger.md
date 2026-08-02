# Workspace Access delivery ledger

| Field | Record |
| --- | --- |
| Supported completion level | `DOMAIN_VERIFIED` |
| Evidence present | workspace replay/conflict; canonical roots; 256-bit random secret; digest-only persistence; known scopes; environment-only authorization; expiry; revocation; redacted decisions; atomic local write |
| Evidence missing | hosted IdP; MFA; OS ACL hardening; multi-process locking; remote vault; tenant isolation; security review; attack testing; production audit trail |
| Substitutes | local JSON registry; bearer credential; injected clock in domain tests |
| Decisions unapproved | identity provider, role model, refresh tokens, device enrollment, vault, retention, incident response and billing identity |
| Forbidden claims | no production authentication; no secure remote access; no compliance certification; no tenant isolation; no password or OAuth support |
