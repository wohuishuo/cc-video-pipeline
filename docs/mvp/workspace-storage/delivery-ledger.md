# Workspace Storage delivery ledger

| Field | Record |
| --- | --- |
| Supported completion level | `DOMAIN_VERIFIED` |
| Evidence present | deterministic namespace provisioning; replay/conflict; workspace separation; state/artifact/temp roots; path confinement; link rejection; current-byte capacity decision; atomic registry; real CLI drill; real multi-workspace Studio composition |
| Evidence missing | hard concurrent reservation; multi-process locking; OS ACL; encryption; backup/restore; object storage; production isolation; corruption recovery; load evidence |
| Substitutes | local filesystem; atomic JSON registry; serial capacity preflight |
| Decisions unapproved | hosted storage vendor, quota tiers, reservation protocol, retention, encryption keys, backup policy and regional placement |
| Forbidden claims | no production tenant isolation; no hard quota enforcement; no durability or disaster-recovery claim; no encrypted storage claim |
