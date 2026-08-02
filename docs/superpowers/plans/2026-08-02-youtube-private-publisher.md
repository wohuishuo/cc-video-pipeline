# YouTube Private Publisher implementation plan

1. Write failing credential, private-policy, resumable-protocol and receipt tests.
2. Implement the independent CLI, contracts, HTTP transport and idempotent operation.
3. Route credential-backed private YouTube uploads through the new public launcher.
4. Add MVP, capability DAG, evidence and operator documentation.
5. Run focused tests, full repository verification and a fake-endpoint drill before merging.
