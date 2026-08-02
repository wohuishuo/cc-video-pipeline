# Client Contracts MVP Plan

## Goal

Create an independent transport-neutral owner for the versioned commands and endpoint projections consumed by the desktop browser, a future mobile app and a future hosted client.

## Contract

- Export one canonical JSON contract bundle atomically.
- Validate Create, Start and Cancel command envelopes without reading workflow state.
- Return a bounded compatibility decision for a semantic client version.
- Keep endpoint scopes and projection ownership explicit.
- Preserve Studio as the only run-state owner.

## Implementation order

1. Add failing bundle, command and compatibility tests.
2. Implement the standard-library contract owner and CLI.
3. Add independent launcher, manifest, README and evidence.
4. Run a real export/validate/compatibility drill.
5. Update repository and Graph Engineering maps.

## Non-goals

No remote identity provider, HTTP hosting, mobile UI, database read, workflow mutation, generated SDK or backward-compatibility promise beyond the declared version window.
