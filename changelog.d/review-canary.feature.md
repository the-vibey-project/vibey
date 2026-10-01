* **gh:** `vibey-gh review-canary` measures whether the sovereign review catches real
  defects. A corpus of diffs against this repository's own code -- 27 with one planted defect
  each, in nine classes, and 14 clean controls -- goes through `local-review` with every
  `[pr_automation.fallback]` setting the pull-request review uses, and recall, the
  false-positive rate (each with a Wilson interval), the no-verdict count and recall per class
  are appended to an append-only ledger, with the model, settings, commit and host. The
  runbook shows the latest measurement; `review-canary.yml` re-measures weekly on the
  sovereign runner and lands it as a pull request; `status` says whether the latest
  measurement meets the declared floor (`[pr_automation.review_canary]`), for the approver
  that will read it. Nothing approves on it yet.
