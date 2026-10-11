* **A BUILD job's prompt now carries the work, not just its title:** the whole prompt an engine
  got was the item's id and title, generic house rules and the verification commands. A local
  20B model given that spent twenty sessions on one item producing nothing usable, searching the
  repository for what it was meant to build; the spec was nowhere in what it was handed, and the
  `.vibey/context/` it could find held an earlier, unrelated job's spec, because the accepted spec
  is published to the checkout's working tree while a worktree is cut from a commit. The prompt
  is now built from the accepted spec and the item's own payload: the objective and first slice,
  every constraint and non-goal (several name the very files to reuse), this item's acceptance
  criteria in full and no one else's, the files it is expected to write, which earlier items are
  already in its branch, and how to start (read `AGENTS.md`, then the named files). The fan-out
  records each item's criteria and files on its job for this. The router block that vibey writes
  into `AGENTS.md` and its siblings no longer sends the engine to `.vibey/context/` as the
  authority: where it disagrees with the task prompt, the prompt wins. An item without those
  fields, or a project with no accepted spec, gets the prompt it always had.
