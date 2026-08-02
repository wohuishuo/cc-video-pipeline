# YouTube OAuth Bootstrap vertical-slice brief

## Outcome

Given a local Google desktop OAuth client JSON and explicit user consent in the system browser, store one refreshable YouTube upload credential in Credential Vault and emit only a redacted connection receipt.

## Boundary

OAuth Bootstrap owns the ephemeral loopback listener, state, PKCE verifier, authorization code and token exchange. Credential Vault owns encrypted persistence and rotation. Video Graph Studio owns only the durable connect/verify Graph projection.

## Definition of done

Domain verification requires state/PKCE, exact-scope, refresh-token, loopback, browser-failure, Vault-injection and redaction tests. Platform integration requires a deliberate real Google consent and successful private upload using the resulting credential.
