# YouTube OAuth Bootstrap capability evidence

- Client-config tests reject web clients and untrusted endpoints while redacting client secret.
- Authorization tests prove loopback IP, state, PKCE S256, offline consent and the single `youtube.upload` scope.
- A real local HTTP callback test rejects the wrong state before showing success, then accepts the exact callback.
- Token tests require a refresh token and exact returned upload scope.
- Vault adapter tests prove the secret exists only in one child environment and select put versus rotate without echoing it.
- Studio adapter tests prove the two-node Connect Graph validates a redacted receipt and an independent active Vault fact.

These are deterministic local substitutes. No Google account was contacted, so the level is `DOMAIN_VERIFIED`.
