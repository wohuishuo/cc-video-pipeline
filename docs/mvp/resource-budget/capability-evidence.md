# Resource Budget capability evidence

- Public owner: `configure`, `reserve`, `renew`, `release`, `describe`, `snapshot`.
- RED assertion: focused tests initially failed with `ModuleNotFoundError: resource_budget`.
- Eight focused owner tests prove configuration replay/conflict, hard byte/slot denial, exact reserve replay, changed-input conflict, renew replay, stale generation rejection, idempotent release, TTL reclamation and same-fingerprint expired-ID reactivation.
- Two real CLI processes competing for one slot produce exactly one `COMPLETED` and one `REJECTED_BUDGET` result.
- Adjacent integration consumes a real Workspace Storage capacity fact, then proves reserve, denial, release and replacement through public launchers.
- Studio composition acquires before a real child, renews by generation and restores all capacity after terminal release.

| Failure | Evidence |
| --- | --- |
| Duplicate | reserve, renew and release replay without extra capacity |
| Conflict | changed configure/reserve input rejected |
| Stale | old generation rejected without mutation |
| Reentry | released ID repeats release; expired same-fingerprint ID reactivates at a higher generation |
| Partial failure | SQLite transaction rolls back before a committed fact |
| Cleanup | release and TTL expiry return capacity; repeated release is safe |

No distributed store, external-writer enforcement, billing or production claim is supported.
