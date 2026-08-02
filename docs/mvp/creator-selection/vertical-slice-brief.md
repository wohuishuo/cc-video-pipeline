# Creator Selection vertical slice brief

Observable result: a verified Creator Manifest plus an exact non-empty set of video IDs becomes one immutable, ordered Creator Selection Manifest.

Creator Selection owns subset validation, source-order projection, source fingerprint lineage, atomic receipt/manifest writes and operation replay/conflict behavior. It does not discover accounts, download media, translate, synthesize voices, compose video or publish.

The same ID set produces the same result regardless of caller order. Unknown IDs, duplicate IDs, empty selections and a changed input under the same operation are rejected before a downstream owner runs.
