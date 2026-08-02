# YouTube OAuth Bootstrap delivery ledger

| Field | Record |
| --- | --- |
| Supported completion level | `DOMAIN_VERIFIED` |
| Evidence present | desktop-client parser; trusted endpoints; system-browser URL; 127.0.0.1 ephemeral callback; state and PKCE S256; exact upload scope; refresh-token requirement; Vault put/rotate child injection; redacted receipt; Studio connect/verify Graph |
| Evidence missing | real Google consent; consent-screen verification; token revocation/expiry operations; DPoP; cross-account protection; authenticated upload using the issued credential |
| Substitutes | deterministic token transport, real local callback and fake Vault child results |
| Decisions unapproved | hosted OAuth, mobile SDK selection, multi-user token custody and automatic public posting |
| Forbidden claims | no real account has been connected by automated evidence |
