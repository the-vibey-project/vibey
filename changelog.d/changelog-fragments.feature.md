* **gh:** changelog fragments. A pull request no longer edits `CHANGELOG.md`: it adds one new
  file, `changelog.d/<slug>.<type>.md` beside the changelog it belongs to, holding its entry,
  so two open pull requests can no longer conflict over the same `## [Unreleased]` lines --
  which GitHub's mergeability never resolved, because it does not run the `merge=union`
  driver, and which cost repeated re-merges of #1295, #1297, #1298 and #1299 in one night.
  The release commit `vibey-gh promote` makes now folds every fragment in under its type's
  heading, deletes it, and cuts `## [Unreleased]` to `## [x.y.z] (date)`, so a release needs
  no hand step; `vibey-gh changelog assemble` runs the fold alone and is idempotent. The new
  `Changelog fragment` check (`changelog.yml`, `vibey-gh changelog check`) refuses a pull
  request into `develop` that changes shipped code without a fragment (unless labelled
  `no-changelog`, a label the check creates itself), adds a malformed one, or edits an
  unreleased section by hand. Declared by
  `[changelog]`, off by default for adopters; on here, for both this changelog and
  vibey-gh's, and the `merge=union` attribute is gone.
