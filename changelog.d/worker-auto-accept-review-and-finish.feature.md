* **`vibey worker --auto-accept-review`, `--auto-finish-local` and `--auto-accept-all`:** the
  rest of the human decisions between DESIGN and a finished local project can be given in advance
  too, each a separate flag for one worker and one project (refused with `--all-projects`).
  `--auto-accept-review` answers the REVIEW approval gate `accept` (never `changes` or `cancel`),
  `--auto-finish-local` answers the deployment choice `local_only` (never `deploy`), and
  `--auto-accept-all` is those two with `--auto-accept-design`. They are not `--auto-answer`, so
  the interview and retry gates stay yours unless you add it, and the startup line names exactly
  what the worker will answer. A deployment gate (`deploy_acceptance` is consent to change real
  infrastructure) and a spending gate are never answered by any flag. Before, an unattended run
  stopped at every acceptance.
