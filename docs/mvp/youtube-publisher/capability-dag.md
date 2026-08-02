# YouTube Publisher capability DAG

```text
credential environment name
  -> redacted OAuth JSON parser
  -> access-token selection or refresh

video + metadata
  -> input fingerprints
  -> forced-private resource
  -> resumable-session creation
  -> streamed file transfer
      -> 308 committed-range resume
      -> bounded 5xx status query and backoff
  -> non-empty external video ID
  -> atomic redacted receipt
      -> duplicate-completed replay
      -> unknown-outcome replay fence
```
