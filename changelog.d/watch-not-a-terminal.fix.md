* **`vibey watch` no longer takes over a pipe:** run with its input or output piped or redirected it printed
  the full-screen escape sequences (colour even with `NO_COLOR` set) and never exited, so a script or an agent
  hung on a screen it could not read. It now prints the same snapshot as `vibey status` and exits; `--replay`
  without a terminal is a usage error.
