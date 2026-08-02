# Workspace Storage capability evidence

- Domain tests prove exact provisioning replay and changed-root/quota conflict.
- Domain tests prove two workspace IDs receive disjoint deterministic roots.
- Path tests reject traversal, absolute and drive-relative input.
- Namespace creation rejects file collisions; runtime queries reject redirected or linked paths.
- Capacity tests count current files and return bounded `ALLOWED` or `REJECTED_QUOTA` results.
- Registry writes use a same-directory temporary file, flush, `fsync` and atomic replacement.
- CLI tests exercise provision, describe, resolve, capacity and bounded error exit codes.
- A real Windows launcher drill provisioned two workspaces and copied a real repository document into only one artifact namespace.

No hard concurrent reservation, multi-process registry lock, OS ACL, encryption, backup, object storage or Studio routing evidence is present.
