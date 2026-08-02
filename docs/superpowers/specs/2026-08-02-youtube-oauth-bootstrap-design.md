# YouTube OAuth Bootstrap design

## Outcome

Add an independently runnable desktop OAuth program that opens the system browser, accepts one loopback callback, validates state and PKCE, exchanges the authorization code for the exact YouTube upload scope, and stores refresh credentials through Credential Vault without returning secrets to Video Graph Studio.

## Owner graph

```text
Google desktop client JSON -> YouTube OAuth Bootstrap -> system browser / loopback callback
                                               -> Credential Vault public CLI
Credential Vault redacted fact -> Video Graph Studio verification
```

OAuth Bootstrap owns ephemeral consent state and code exchange. Credential Vault owns persistent encryption and lifecycle. Studio owns only the connect Graph and public progress projection.

## Invariants

- Bind callback only to `127.0.0.1` on an ephemeral port.
- Use a system browser, never an embedded webview.
- Request only `https://www.googleapis.com/auth/youtube.upload`, offline access and explicit consent.
- Generate and validate unpredictable state plus PKCE S256 verifier/challenge.
- Require the returned scope and a non-empty refresh token.
- Send client secret and refresh token to Credential Vault only through one child environment.
- Never persist authorization code, state, verifier, access token, refresh token or client secret outside the encrypted Vault.
