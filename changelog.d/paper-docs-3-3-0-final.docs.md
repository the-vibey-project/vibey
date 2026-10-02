* **paper:** the final pass for 3.3.0 brings the research paper current with everything
  merged after #1324, up to `7fe72281b` (#1340). It reports the review canary's first
  measurement of the sovereign reviewer's recall (18 of 25 planted defects caught, Wilson
  95% 0.524 to 0.857; 0 of 14 controls blocked), with the two misses passed while the
  reviewer's own summary named the defect; the large-diff study, as what it is, in
  progress (mechanism and screening only, on one diff), with production unchanged; the
  lane's record under #1316 (every verdict on a diff reviewed in one request) and the one
  four-part verdict before it (#1307); the host's weekly health record and its measured
  memory budget (about 49 GiB of demand on 24 GiB, swap-outs about 85% of SSD writes); the
  revoke race's third message and its cause in the tests; the KEDA contract, the Arch
  mirror fallback, the declared and expiring advisory exceptions, and the push-gate tests'
  isolation; and the forge's record of who merged, extended to #1340. The paper's history
  figures stay pinned at `d4c4e1f8`. The root changelog fragment for #1316 no longer says
  that the review reaches a verdict on a large pull request. The README and the
  documentation home link the host-health and host-optimization pages, and the sovereign
  review runbook says what the canary does not measure.
