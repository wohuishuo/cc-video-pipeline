# YouTube OAuth Bootstrap delivery ledger

| Field | Record |
| --- | --- |
| Supported completion level | `DOMAIN_VERIFIED` |
| Evidence present | local browser-oriented Connect Graph; trusted desktop config; loopback/state/PKCE protocol; exact upload scope; refresh-token gate; Vault public-boundary storage and verification; secret-free Studio persistence |
| Evidence missing | real Google consent, app verification, DPoP, revocation operations and a private upload using the resulting credential |
| Substitutes | local callback HTTP test and deterministic token/Vault adapters |
| Decisions unapproved | hosted or mobile OAuth ownership and commercial multi-user custody |
| Forbidden claims | Graph completion under substitutes is not a connected real YouTube account |
