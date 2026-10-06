* **local-review:** the `--outcome` record now carries the `model`, the `runner` (its
  `RUNNER_ENVIRONMENT`, `RUNNER_OS`, `RUNNER_ARCH` and `RUNNER_NAME`) and `requests`: one
  entry per request attempt and per slot probe, with the characters and estimated tokens it
  sent, its deadline and the rates it was derived from, how long it took, how it ended as a
  code from the closed vocabulary, and Ollama's own counters and rates when the model
  answered. The record is kept on disk while a request runs, so a cancelled run still names
  the request it was waiting on. Fields are only added to `vibey-gh.local-review/1`; nothing
  the review decides, prints or exits with changes.
* **review-timings:** `vibey-gh review-timings PATH... [--json]` reads those records (files,
  or directories of downloaded artifacts) and reports per model and runner the median, p10
  and p90 prompt and output tokens a second, the requests that timed out and at what prompt
  sizes, and -- from at least `--minimum` answered requests (default 5) -- suggested
  `--prompt-tokens-per-second` and `--output-tokens-per-second` (the p10, rounded down).
  Files that are not local-review records are named and skipped.
