# Studio HTTP contract-discovery drill

On 2026-08-02, `scripts/drills/studio-contract-discovery.ps1` started a real loopback HTTP server with an admission adapter that would fail the drill if invoked. Two credential-free `GET /api/v1/contracts` requests both returned HTTP `200` and the same cached Client Contracts CLI result.

| Fact | Result |
| --- | --- |
| Contract version | `1.0` |
| Commands | `CMD-RUN-CREATE`, `CMD-RUN-START`, `CMD-RUN-CANCEL` |
| Discovery scope | `null` (public) |
| Same server-generation result | `true` |
| Bundle SHA-256 | `1a6e122f7d0401ac849a9b2866187e163821b641ef8f3e83cf91537f5e47b48b` |

The browser contract tests require this discovery before enabling mutation and derive command-envelope version from the bundle. Malformed or unavailable CLI results return bounded HTTP `503` without child diagnostics.

This is local contract discovery evidence. It does not prove a mobile client, remote authentication, hosted compatibility, SDK generation or deprecation operations.
