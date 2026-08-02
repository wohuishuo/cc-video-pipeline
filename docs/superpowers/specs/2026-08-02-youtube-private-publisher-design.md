# YouTube Private Publisher design

## Outcome

Add an independently runnable `youtube-publisher` MVP that accepts one local video, one metadata file and one credential environment variable, performs a YouTube Data API resumable upload with `privacyStatus=private`, and commits a redacted receipt containing a non-empty YouTube video ID.

## Ownership

- Credential Vault owns encrypted secret custody and injects one credential JSON value into the child environment.
- YouTube Publisher owns OAuth refresh, resumable-session protocol, private-only policy and upload receipts.
- Platform I/O selects YouTube Publisher for credential-backed YouTube execution; its existing third-party adapters remain isolated.
- Publication owns confirmation, serial job checkpoints and cross-platform manifests.
- Video Graph Studio owns Graph/run projection only.

## Credential contract

The injected JSON contains either `accessToken`, or the complete refresh set `clientId`, `clientSecret`, `refreshToken`. Refresh credentials are preferred when present. No token, client secret, refresh token, credential hash or resumable-session URL may appear in argv, stdout, stderr or receipts.

## Failure semantics

- Invalid inputs and OAuth/API 4xx responses are bounded failures.
- A completed API response without a non-empty video ID is failure.
- Interrupted or exhausted resumable recovery after a session exists is `UNKNOWN`; automatic replay is fenced to avoid a duplicate upload.
- A matching completed receipt returns `DUPLICATE_COMPLETED` without contacting YouTube.

## Evidence boundary

Deterministic fake-transport tests can prove protocol construction, resume offsets, policy and redaction. Only a deliberate upload to an authenticated channel can raise the capability to `PLATFORM_INTEGRATED`.
