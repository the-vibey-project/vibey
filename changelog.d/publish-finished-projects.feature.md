* **Publishing a finished project:** the last step of a delivered project can now get its work
  off the machine. With `[publish] mode = "interview"` or `"auto"`, declining deployment no
  longer finishes the project: a `review.publish` job pushes the integration branch and opens a
  pull request (a draft by default), or, for a project with no remote, creates a new GitHub
  repository (private by default) and pushes to it, and only then is the project DONE. The
  `interview` mode raises a `publish_interview` gate showing exactly what would be pushed and
  where; `accept_defaults` publishes that, `skip` finishes locally (its declared default, and
  it never times out to a default), and `custom` changes named fields. `vibey worker
  --auto-publish` answers it `accept_defaults`; it is its own flag, never implied by
  `--auto-accept-all`. Nothing is forced and the base branch is never pushed to. Because a work
  item can write the repository's git config, publishing refuses one that sets a command git
  would run (`core.sshCommand` and similar) and a remote that is not an https or ssh address,
  and runs git with hooks off. It needs `gh` logged in; otherwise the job parks on an
  `engine_misconfigured` gate. `[publish] mode` defaults to `off`, so nothing changes unless
  set. Before, a run ended on a local branch and the push was by hand.
