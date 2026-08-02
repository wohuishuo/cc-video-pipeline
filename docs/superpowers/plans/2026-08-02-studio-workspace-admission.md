# Studio Workspace Admission Composition Plan

## Goal

Compose the independently verified Workspace Access MVP with Video Graph Studio's loopback HTTP boundary. Keep identity policy outside Graph/Run/Queue owners and preserve the zero-configuration local mode.

## Contract

- Secure mode binds one Studio process and data root to one configured workspace.
- Workspace roots are queried through Workspace Access's public CLI.
- Static UI and health remain readable; all other API routes require the configured workspace plus an appropriate Bearer scope.
- GET queries require `runs:read`; folder browsing requires `artifacts:read`; mutations require `runs:write`.
- The plaintext credential travels only in an environment variable to the Workspace Access subprocess and is absent from argv, logs and decisions.
- Browser credentials stay in `sessionStorage` and are removed from the URL fragment immediately if bootstrapped there.

## Implementation order

1. Add failing Workspace Access describe-query tests.
2. Add failing HTTP admission tests for missing, wrong-workspace, read and write scope.
3. Implement the CLI composition adapter and transport admission gate.
4. Add optional launcher arguments and browser access dialog/session headers.
5. Verify default local mode, secure real CLI mode and denial/redaction evidence.

## Non-goals

No LAN binding, multi-tenant database, OAuth, refresh token, hosted identity provider, billing or remote secret vault in this slice.
