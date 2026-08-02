# Client Contracts Delivery Ledger

| Field | Record |
| --- | --- |
| Supported completion level | `DOMAIN_VERIFIED` |
| Evidence present | deterministic atomic bundle/show; exact replay; strict Create/Start/Cancel validation; endpoint scopes; ownership map; semantic client compatibility; unauthenticated Studio HTTP discovery; browser-discovered command version; real launcher/loopback drills |
| Evidence missing | generated SDK; remote identity; mobile application; deprecation and production compatibility operations |
| Forbidden claims | no mobile app; no hosted API; no authentication; no workflow-state ownership |

On 2026-08-02, the public launcher exported contract `1.0`, validated `CMD-RUN-START` and returned `COMPATIBLE` for client `1.2.0`. Bundle SHA-256: `77f0d6d953f8946f77a30592200db9ccee4b2624b78775225f1897981664b031`.

After adding self-described discovery, the real public launcher and loopback Studio endpoint returned contract `1.0` twice without entering workspace admission. Commands were Create, Start and Cancel; discovery scope was `null`; canonical bundle SHA-256 was `1a6e122f7d0401ac849a9b2866187e163821b641ef8f3e83cf91537f5e47b48b`. See [the complete drill](studio-http-discovery-drill.md).
