* **A local BUILD plan is fewer, larger slices, and a dependent item waits for the code it builds
  on:** a real run of a seven-item plan showed two faults. Three of the items (`c4`, `c9`, `c10`)
  had no files to write and only restated checks every item already runs, and the item that ran
  first, `c4`, started before the walking skeleton was integrated, so its worktree was the bare
  base and a local model spent 55 turns searching for routes that were not there. (1) The
  sovereign decomposer now folds an item that touches no file into the dependency it verifies: its
  criteria and checks move there, that item inherits what the folded one waited for, and anything
  that waited on the folded item waits on it instead (an item with no dependency to fold into
  stays for the plan check to name). The prompt says a check is never an item. (2) A dependent `build.implement` job
  now defers, without using an attempt and without touching an engine circuit, until a succeeded
  `build.integrate` job covers each item it builds on, so its branch is cut from the integration
  branch with their code on it. The queue only waited for the dependency's implement job, which
  finishes before its verify and integrate jobs, and those were last in line behind the other
  items.
