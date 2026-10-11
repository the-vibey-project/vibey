* **How many work items a plan has follows the spec, not a number:** a local DECOMPOSE is no
  longer told how many items to make, nor re-asked for an item it made too large. The prompt now
  says there is no target count: keep work that belongs together in one item (routes, data, tests
  and docs for one feature), split where the work really divides (a different concern or layer,
  something that must exist before the next piece can be built or checked, or more than one
  engine session can finish), never split only to make items smaller and never merge dependent
  pieces to make fewer. What is still checked is what makes a plan unsound: every criterion
  claimed, dependencies listed first, files that exist or are planned, no item that writes no
  file, and verification that can run (no pytest on a TypeScript file).
