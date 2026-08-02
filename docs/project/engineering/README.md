# Engineering Rules

## Operating documents

- [Graph and Loop Engineering](graph-loop-operating-model.md)
- [State ownership rules](rules/state-ownership-rules.md)
- [Delivery operating model](rules/delivery-operating-model.md)
- [Review checklist](rules/review-checklist.md)

## Contract and lifecycle

- Commands carry `contractId`, `contractVersion`, `operationId` and `correlationId`.
- Same operation ID plus same canonical fingerprint replays the original result.
- Same operation ID plus different input is `REJECTED_CONFLICT`.
- Run versions advance under optimistic checks; terminal replay never repeats work.
- Startup marks abandoned active steps `INTERRUPTED`; resume starts at the first missing checkpoint.

## Process safety

- One control-plane Worker and one child process run at a time.
- Child processes receive argv arrays, never interpolated shell strings.
- Cancellation affects only the child handle owned by the active adapter.
- Logs are append-only and exclude cookie contents, access tokens and media bytes.
- The HTTP listener is restricted to `127.0.0.1`.
- Folder paths are resolved before allowed-root containment checks.

## Evidence levels

`DESIGNED`, `IMPLEMENTED`, `DOMAIN_VERIFIED`, `PLATFORM_INTEGRATED` and `PRODUCTION_VERIFIED` are distinct. Contract tests cannot prove external Edge availability, authenticated social publication, crash-safe cloud durability, security, scale or commercial operations.
