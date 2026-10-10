* **`vibey doctor --conformance`:** the wait for an engine's run directory is now set by
  `VIBEY_CONFORMANCE_POLL_SECONDS` (seconds; default unchanged at 30). A local model on
  ordinary hardware needs far longer than a hosted engine to answer a first turn, and the
  fixed window failed `run_dir_shape`, `snapshot_schema`, `done_marker` and
  `structured_verdict` together for a reason that was the host's speed, so the only way to
  record conformance for gptossloop was to edit the installed package. A value that is not a
  finite number above zero is refused with exit 2, naming the variable, before any engine is
  started; unset keeps the default.
