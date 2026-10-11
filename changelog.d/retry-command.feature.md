* **`vibey retry PROJECT_ID`:** one command to get a stalled project moving again. It stops this
  user's `vibey worker` processes as `recover --stop-workers` does, answers each of the project's
  `attempts_exhausted` gates with a grant (`--max-attempts`, default 10), and with `--start-worker`
  starts `vibey worker --project PROJECT_ID` detached, passing along every argument after `--`
  and appending to a per-project log (`--log` to choose it). Before, that was `recover`, `gates`,
  `answer --raw '{"max_attempts": N}'` and a hand-written restart script. Only exhausted-attempts
  gates are answered; any other open gate is a decision and is only named. Each grant is a named
  request, so running it twice answers a gate once, and `--dry-run` says what each step would do.
