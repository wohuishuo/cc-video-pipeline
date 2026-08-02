# YouTube OAuth Bootstrap MVP

Connect one YouTube account with Google's desktop OAuth flow. The program opens the system browser, listens only on an ephemeral `127.0.0.1` callback, validates state and PKCE S256, requests only `youtube.upload`, and sends the refresh credential directly to Credential Vault through a child environment.

```powershell
.\apps\youtube-oauth-bootstrap\run.ps1 connect `
  --client-config "$HOME\Downloads\client_secret.json" `
  --vault "$env:LOCALAPPDATA\VideoGraphStudio\credential-vault.json" `
  --credential-id youtube-main --label "Main YouTube" `
  --output-dir "$env:LOCALAPPDATA\VideoGraphStudio\oauth" `
  --operation-id connect-youtube-main --json
```

The first JSON line contains a safe authorization URL and the final line contains a redacted result. Client secret, authorization code, state, verifier, access token and refresh token are absent from both output and the receipt. Google requires the OAuth client itself to be created manually in Cloud Console; this program cannot create it for you.
