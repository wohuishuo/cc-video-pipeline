# Credential Vault vertical slice brief

Observable result: an operator stores one platform credential without placing its plaintext in argv, files or public output, inspects redacted metadata, injects it into one child adapter and can explicitly rotate or irreversibly revoke it.

Credential Vault owns encrypted local custody and lifecycle. Platform adapters own credential interpretation and login behavior. Workspace Access owns caller admission. Publication owns plans and receipts. Graph Studio may retain only a credential ID.
