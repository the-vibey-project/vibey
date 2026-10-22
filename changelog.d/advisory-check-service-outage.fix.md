* **`vibey-gh advisory-check` can report an advisory-service outage as a warning:** a
  network timeout or 5xx from the npm advisory endpoint now says which service did not answer
  instead of `npm audit failed:` with no reason. The gate still fails closed by default; a
  repository may set `[advisories] on_unavailable = "warn"` to print a `::warning::` naming
  the workspace and continue unaudited, and this repository does. A real advisory, a
  malformed report or a missing lockfile still fails.
