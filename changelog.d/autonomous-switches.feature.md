* **`vibey worker --auto-record-research-gaps` and `--autonomous`:** DESIGN research on a local
  model has no search backend and no evidence directory unless you set one, so it parked a
  `research_evidence` gate per topic and an unattended run sat there (three at once on a real
  project: `prior-art`, `libraries`, `api-docs`). `--auto-record-research-gaps` makes research
  record the topic as not researched and go on, answers a gate already parked so it runs again,
  and the spec says what was not researched, so nothing is invented. `--autonomous` is every
  switch that is safe to leave on for an unattended run in one flag: `--auto-answer`,
  `--auto-accept-all` and `--auto-record-research-gaps`. It never turns on `--auto-publish` (that
  sends the work to GitHub), a deployment or a spending gate. Both act on one project.
