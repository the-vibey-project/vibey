* **A BUILD retry that must change engine no longer defers for ever on a pool with only one:**
  from the third attempt a BUILD job escalates its effort (low to standard, then to high), and an
  escalated retry is required to rotate away from the engine that just failed. On a pool with no
  other engine that excluded the only candidate, selection found nobody, and the job was deferred
  every five minutes with no park, no failure and nothing on the ledger (a one-engine local pool
  did exactly that on its third attempt, with `gptossloop: excluded for this attempt (a retry that
  must rotate away)` the only trace). The rotation now applies only when another engine remains
  after the exclusions; otherwise the retry still escalates its effort and stays on the engine it
  has, as a same-tier retry does. An unknown pool keeps the rotation absolute, and a pool with a
  second engine rotates as before. The same rule `build.verify` already had for reviewer
  independence.
