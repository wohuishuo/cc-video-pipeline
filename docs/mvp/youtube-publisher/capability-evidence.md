# YouTube Publisher capability evidence

- Credential parsing accepts an access token or complete refresh tuple and redacts representation and errors.
- Metadata normalization always emits `status.privacyStatus=private`.
- Fake HTTP transport proves OAuth refresh, resumable session creation, `308` offset continuation, non-private rejection and non-empty video ID.
- Interrupted/exhausted sessions become `UNKNOWN`; the receipt fences automatic replay.
- Platform I/O routing tests prove credential-backed YouTube execution selects this public launcher and consumes its external ID.

The protocol follows Google's [resumable upload guide](https://developers.google.com/youtube/v3/guides/using_resumable_upload_protocol) and [OAuth refresh flow](https://developers.google.com/identity/protocols/oauth2/web-server). No authenticated channel was contacted, so the evidence is `DOMAIN_VERIFIED` only.
