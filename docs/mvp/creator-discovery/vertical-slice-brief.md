# Creator Discovery vertical slice brief

Observable result: one supported HTTPS creator URL becomes a versioned, ordered and deduplicated manifest of canonical video URLs.

Creator Discovery owns profile enumeration, pagination checkpoints, adapter identity and its manifest/receipt. It does not download media, monitor accounts, translate, render voices, compose video or publish.

Inputs are a profile URL, `maxItems`, operation ID and optional authentication-material file. Authentication contents and paths are never persisted. Outputs are `creator-manifest.json` and `discovery-receipt.json`.

Retries reuse a verified complete manifest or continue from the committed cursor. Changing the URL, limit, adapter or authentication fingerprint under the same operation conflicts.
