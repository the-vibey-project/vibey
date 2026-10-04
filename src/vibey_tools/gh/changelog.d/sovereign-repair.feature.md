* **pr automation:** a review that fails on findings can be corrected by an open-weights
  model instead of waiting for a person. Declared in `[pr_automation.sovereign_repair]`,
  gptossloop on a GitHub-hosted runner edits the branch from the review's findings, the
  guarded repair step publishes the patch, and CI and the exact-head review run again, within
  the bounded `max_repair_attempts` budget, which a new `pr-automation repair-budget` action
  now checks on the same-run path too. A spent budget or an unappliable patch labels the pull
  request for a person ([#1400](https://github.com/the-vibey-project/vibey/issues/1400)).
