* **version:** `[version] regenerate` declares commands (argv lists, never a shell line) that
  re-derive files embedding the version. They run after every release bump, and whatever
  they rewrite joins the release commit, as the lockfile and the pinned workflows already
  do. A command that fails stops the release. Dev builds skip it. No key, no change.
