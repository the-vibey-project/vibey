* **`vibey new --accept-spec-json FILE` skips DESIGN:** a spec an operator has already reviewed
  makes the DESIGN interview, its research and its spec synthesis work whose output is thrown
  away, and `vibey worker --accept-spec-json` could only act once every DESIGN job had settled, so
  all of it ran first (a real run then hung on three research gates for evidence nobody needed).
  Given the spec at creation, the project moves into DESIGN with no interview job, the spec is
  saved and accepted at once through the same acceptance guards as `vibey design accept` (visual
  design declined, the ledger naming `new-with-spec`), and BUILD's decomposition is enqueued. A
  spec that cannot be read is a usage error before any project exists; one the acceptance refuses
  leaves the project in DESIGN with the spec saved, so `vibey design accept PROJECT --spec-json
  FILE` finishes it. The worker's `--accept-spec-json` keeps its meaning for a project already
  interviewing, and its help now points here.
