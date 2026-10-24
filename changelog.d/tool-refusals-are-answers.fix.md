* **A refused tool call no longer ends a local run:** a model that asked to read an absolute path (`/x.py`) or one
  outside the worktree crashed the whole run with a `ValueError`. Every tool now returns the refusal as an answer for
  the model to correct. Found by the model benchmark in ADR-0093, #1662.
