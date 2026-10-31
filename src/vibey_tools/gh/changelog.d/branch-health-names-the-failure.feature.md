* **The red-branch issue names what failed:** `branch-health` used to name the failed check and link the run, so
  learning that #1680's cause was `tests/meta/test_paper_figures.py` meant opening the run and reading its log. The
  tracking issue and its per-run comment now carry, for each failed job, the failed step (linked), the first failing
  test id and its job-log line where the log makes them available, and a reproduction command looked up in the new
  `[branch_health.reproduce]` map (`"check"` or `"check :: step"`, with `{test}` filled in, shell-quoted). A log that
  cannot be read, a check with no entry and a step the forge did not report are each said out loud, never guessed.
  New keys: `reproduce`, `test_id_pattern`, `log_bytes`. #1690.
