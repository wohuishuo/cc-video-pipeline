# Workspace Storage Delivery Ledger

| Field | Record |
| --- | --- |
| Supported completion level | `DOMAIN_VERIFIED` |
| Evidence present | independent launcher and manifest; deterministic per-workspace roots; exact replay/conflict; path confinement; symlink/link rejection; current-byte capacity decision; atomic registry replacement; real two-workspace CLI lifecycle; real Studio routing into separate state/artifact roots |
| Evidence missing | hard concurrent reservations; multi-process locking; OS ACL; encryption; backup/restore; remote object storage; production isolation, corruption and load evidence |
| Safe substitutes | local filesystem; one registry writer; serial preflight capacity query |
| Decisions unapproved | storage vendor, tenant quota tiers, reservation/lease protocol, encryption, backup, retention and regional placement |
| Forbidden claims | no production tenant isolation; no hard quota enforcement; no high durability; no disaster recovery; no encrypted-at-rest claim |

## Live CLI evidence

On 2026-08-02, workspaces `alpha` and `beta` returned `COMPLETED` below one canonical storage root and received different workspace roots. Repeating `alpha` returned `DUPLICATE_COMPLETED`. A real 8,765-byte repository README copy was written below only `alpha/artifacts`; the capacity query returned `ALLOWED` with 991,235 bytes available, a request for 991,236 bytes returned `REJECTED_QUOTA` with exit code `3`, and `../escape` returned `REJECTED_PATH` with exit code `2`. Registry SHA-256: `68ba9c37f9d56948affae3a10b0b0b36a3eed5c23b469086692fd72144c649a8`.

Studio composition evidence is recorded in [the multi-workspace routing drill](../video-graph-studio/multi-workspace-routing-drill.md).
