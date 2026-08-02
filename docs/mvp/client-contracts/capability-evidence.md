# Client Contracts capability evidence

- Tests prove the bundle names Create, Start and Cancel commands, route scopes and authoritative state owners.
- Export tests prove byte-identical replay and same-directory atomic replacement.
- Validation rejects wrong versions, unknown fields and unbounded identities.
- Compatibility tests accept declared `1.x` clients and reject older or future majors.
- A real launcher drill exported a bundle, validated a Start command and returned `COMPATIBLE` for client `1.2.0`.

No HTTP publication, generated SDK, remote identity, mobile UI or production compatibility evidence is present.
