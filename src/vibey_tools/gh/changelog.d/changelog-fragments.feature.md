- **Feature:** changelog fragments (`[changelog]`). A change is recorded as a new file,
  `changelog.d/<slug>.<type>.md`, never as an edit to the changelog, so concurrent pull
  requests stop conflicting over one unreleased section -- a conflict GitHub reports even when
  a `merge=union` attribute would resolve it, because its mergeability never runs the driver.
  `vibey-gh changelog assemble` files each fragment under its type's `### ` heading in the
  unreleased section (creating the section or heading where absent, in `types` order, never
  twice) and deletes it; `vibey-gh promote` and `vibey-gh version --apply` do that in the
  release commit and cut each `versioned` changelog's section into the version's own. `vibey-gh
  changelog check`, rendered as `changelog.yml` ("Changelog fragment"), refuses a pull request
  that changes a `require_for` path without a fragment unless it carries `skip_label`, one with
  a malformed fragment, and one that edits an unreleased section directly. Off by default.
