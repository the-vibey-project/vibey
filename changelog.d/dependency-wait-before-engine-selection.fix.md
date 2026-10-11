* **A work item that is waiting for what it builds on no longer counts as an engine selection:**
  the wait was decided after an engine was chosen, so every poll of a waiting dependent added one
  to that engine's selection count (and so to the rotation's bookkeeping) with no session behind
  it, and the 60-second retry left an item idle for up to a minute after its dependency had
  integrated. The wait is now decided before an engine is chosen, and it polls every five seconds.
