# Creator Batch vertical-slice brief

| Field | Contract |
| --- | --- |
| Observable result | One Creator Manifest becomes one complete, ordered set of localized MP4 derivatives, with exactly one creator item active at a time and durable retry of incomplete items. |
| Use cases | `localize` commands the loop; the receipt reports continuation; the final manifest reports committed item/localization facts. |
| State owners | Creator Discovery owns canonical URLs; five child MVPs own their artifacts; Creator Batch alone owns item continuation; Studio owns only its run projection. |
| Protected invariants | immutable input fingerprint, stable child IDs, maximum item concurrency one, hash-fenced reuse, conflict-before-side-effect, no full success under partial failure. |
| Decision gates | retention/deletion, public posting, hosted scheduling, and commercial tenant policy remain unapproved. |
| Non-goals | parallel processing, publication, translation-quality certification, live platform proof, descendant process production fencing, and power-loss verification. |
