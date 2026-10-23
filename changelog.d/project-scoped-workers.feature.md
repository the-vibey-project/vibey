* **Pause, recover and retry one project without touching the others:** `vibey recover --project ID --stop-workers`
  and `vibey retry ID` now stop only that project's workers (`vibey worker --project ID`) instead of every worker
  this user runs. A worker that serves every project is left running and named; because it may hold one of the
  project's leases, `recover` then resets none and exits 1 until you add `--include-shared`, so a job is never run
  twice. `--all` still stops them all.
