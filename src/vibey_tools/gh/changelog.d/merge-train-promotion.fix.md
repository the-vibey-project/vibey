* **merge train:** the train dispatches `promote-to-main.yml` itself after it merges
  something. The PR review gate starts the train with `GITHUB_TOKEN`, and GitHub fires no
  `workflow_run` for the completion of a run that token started, so promotion's
  `workflow_run: Merge train` trigger never saw the train's runs: from 2026-09-28 every
  promotion to `main` needed a hand dispatch
  ([#1400](https://github.com/the-vibey-project/vibey/issues/1400)).
