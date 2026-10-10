* **`vibey recover --stop-workers`, `--grace` and `--dry-run`:** one command for a stuck queue.
  `vibey recover` only reset the database rows, so a worker that was still alive (or whose
  terminal had closed behind a hung runner) kept its jobs and had to be hunted down with `ps`
  and `kill` first. `--stop-workers` lists every `vibey worker` this user is running, and
  everything each started, signals them (SIGTERM, then SIGKILL after `--grace`), and only then
  resets the leases. It never touches another user's processes, itself or what started it, and
  if anything survives SIGKILL it exits 1 without resetting a lease, since resetting a live
  worker's leases would run its job twice. `--dry-run` shows the plan and the count and changes
  nothing.
