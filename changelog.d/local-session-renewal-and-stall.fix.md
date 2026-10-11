* **A long local session no longer degrades into giving up:** the first section of a real build
  ran past 100 turns with ninety thousand tokens of its own history in every request, and by then
  the model was importing functions that did not exist, calling a file it had written itself
  "corrupted", writing "Cannot finish." into a file and running `echo done`. Two things changed
  in `qwenloop` (which drives gptossloop and qwenloop). Once the conversation passes about
  24,000 estimated tokens, the older turns are replaced by a deterministic summary of what the
  session did (files written, edited and read, the last commands and how they ended) while the
  plan and the newest messages stay, and `context.renewed` is recorded. And a session that has
  made no tool call it had not made in its last twenty calls for eight turns in a row now fails
  as `stalled` instead of spending the rest of its turns, judged on the calls and not on what the
  model says. The work brief also now tells the engine to find and read the closest existing
  code before writing, to import only what exists, and to stop and say what is missing rather
  than write placeholders. Both limits are `run()` arguments (`context_renewal_tokens`,
  `max_stalled_turns`; 0 turns each off).
