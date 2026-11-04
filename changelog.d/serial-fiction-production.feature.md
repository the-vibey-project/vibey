* **Serial and found-document fiction now has a reproducible build method:** the new
  `pipeline-serial-fiction-production` skill makes every downstream file a pure function of the
  drafts. It carries the rules a three-volume log novel (248 logs, eleven document forms) learned
  by building by hand: one source with a `--check` at every generation step, a per-unit manifest
  instead of a driver in a scratch directory, computed facts, canon searched before it is written
  and reconciled honestly with the author's decision documents, standing style rules as a linter
  applied to every volume, found-document forms that are looked at as rendered pages, and
  determinism across machines. The release-engineering retrospective gains three failures from the
  same build: a font the CI runner's TeX packaging omitted (vendor it), a workflow that stayed red
  across merges unexamined, and unit tests that CI never ran. Plugin `content-engineering-pipeline`
  is now 0.3.0; the catalogue has 805 skills.
