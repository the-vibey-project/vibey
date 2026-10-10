* **sovereign runner:** `runner install --load` no longer fails with `launchctl bootstrap failed
  (exit 5)` when it replaces a running supervisor. `launchctl bootout` returns while launchd is
  still stopping the old service, so the load landed in that window. The installer now waits for
  the label to disappear, then retries a load that still answers 5, both bounded by the new
  `[runners] launchd_settle_seconds` (default 60; 0 tries once). Any other refusal is still
  reported at once.
