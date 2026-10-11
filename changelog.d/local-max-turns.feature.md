* **`vibey worker --local-max-turns N|unlimited` (and `VIBEY_LOCAL_MAX_TURNS`):** the turn limit
  every local runner session (gptossloop, qwenloop) is started with. A BUILD piece runs at effort
  `low`, which the engine table maps to `--max-turns 16`; a small local model that needs many tool
  calls to read a repository hit it on the very first piece (`reason: turn_limit` at turn 16). A
  turn limit is a cost control and a local model costs nothing per turn, so the setting replaces
  every effort's limit with a number, or with `unlimited`, which is handed over as 100000, a count
  no session reaches. A session still ends when it reports the task done, is stopped or fails.
  Paid engines keep their limits and ULTRA (which has no flag) stays as it is. A bad value exits
  with a usage error naming the setting. `vibey retry` passes it through after `--`.
