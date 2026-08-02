# YouTube OAuth Bootstrap capability DAG

```text
Google desktop client JSON
  -> trusted endpoint and client-type validation
  -> 127.0.0.1 ephemeral callback
  -> unpredictable state + PKCE S256
  -> system-browser youtube.upload consent
  -> exact callback path/state/code
  -> authorization-code exchange
  -> exact granted scope + refresh token
  -> Credential Vault child environment
  -> active provider-bound credential fact
  -> redacted connection receipt
```
