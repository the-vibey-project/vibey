* **A local session's context stays small instead of growing with every turn:** measured on a
  real 130-turn session, every token of growth was a tool result (search 45%, open_file 20%, find
  15%, shell 14%) and the session read 3.8M tokens to make seven writes, because each turn resends
  the whole history. `qwenloop` now keeps only the newest four tool results whole (plus the last
  shell result, the freshest verdict) and reduces older long ones to a one-line stub the model can
  re-ask; replaces the body of an older `write_file` / `edit_file` call, which is on disk, with a
  note; folds long shell output to its first 20 and last 40 lines; answers an identical read whose
  result has not changed with "same result as turn N"; and shows the model, at the end of every
  request but never in its history, which of the item's planned files are written and how the
  last command ended. A new `outline` tool lists a file's declarations (or only its exports) for a
  few dozen tokens, so the engine need not read a file to learn what to import. Default limits are
  tighter: `search` 40 matches, `find` 60 paths, 160 characters a line, 12,000 characters a tool
  result (a whole 435-line README still fits). Every request's size is recorded by what it is in a
  `context.composition` event. Replaying the recorded session through the new policy keeps the
  context near 5,000 to 10,000 estimated tokens where it grew to 48,000, 75% fewer tokens read over
  the run. Each lever is a field of `ContextEconomy`; `ContextEconomy.off()` restores the old
  behaviour, and the limits are the existing `[tools]` settings.
