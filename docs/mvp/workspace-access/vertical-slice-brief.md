# Workspace Access vertical slice brief

Observable result: an operator creates a workspace identity, issues a time-bounded credential with explicit scopes, receives the plaintext once, verifies an authorization decision through an environment-only secret input and can revoke it.

Workspace Access owns identity, allowed-root policy and credential lifecycle. Graph Studio owns runs. Platform adapters own platform credentials. A future hosted transport consumes authorization decisions but cannot edit the registry through run commands.
