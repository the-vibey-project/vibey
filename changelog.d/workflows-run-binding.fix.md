* **hub:** `GET /api/v1/workflows/runs/{request_id}` no longer hands a run's output to any
  device that holds the `workflows` scope. The hub now mints each request id bound to the
  principal that started the run, as a nonce and an HMAC tag under a 32-byte key kept
  owner-only in its state directory (`run.key`). A device reads back only its own runs. Any
  other id gets the 404 an unknown run gets, and the forge is never asked. The host still
  reads any run (ADR-0085).
