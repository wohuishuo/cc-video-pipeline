# Studio contract discovery design

## Promise

Desktop browser, future mobile applications and future hosted clients can discover the exact current Video Graph Studio command, endpoint, scope, compatibility and ownership contract from one unauthenticated loopback HTTP endpoint.

## Owners and boundary

- Client Contracts remains the sole bundle writer and exposes a public `show` command.
- Video Graph Studio invokes only `apps/client-contracts/run.ps1`; it does not import or reconstruct the bundle.
- HTTP transport exposes the returned immutable bundle at `GET /api/v1/contracts` before workspace routing.
- The browser consumes the discovered contract version when constructing envelopes. It does not own compatibility or command truth.

## Lifecycle

1. Studio starts and creates a Client Contracts CLI adapter.
2. The first discovery request invokes `show --json`, verifies the result shape and caches the immutable result for the server generation.
3. Contract discovery and health are public so a client can negotiate before it has a workspace credential.
4. The browser requires all three run commands and the relevant endpoint declarations, then uses the discovered version for every envelope.
5. Missing, malformed or incompatible discovery disables mutation and fails closed visibly.

## Security and failure

The bundle intentionally describes public API shape and scopes but contains no credentials, workspace roots or run state. Child stderr/stdout is never forwarded when the boundary fails. Workspace authorization still runs on every scoped endpoint. A changed contract requires a new server generation and declared compatibility; the cache cannot silently change mid-session.

## Verification boundary

Owner tests cover canonical show/export identity. Studio tests cover public pre-auth discovery, CLI parsing/caching and malformed failure. Browser contract tests cover discovered-version envelopes and fail-closed bootstrap. A real loopback drill proves Client Contracts CLI to Studio HTTP. This is not a mobile app, hosted API or remote authentication claim.
