- **Feature:** `vibey-gh review-canary` -- `check`, `show`, `run`, `render [--check]`,
  `status [--json]` -- measures the sovereign review's recall and false-positive rate against
  a corpus of planted defects and clean controls (`[pr_automation.review_canary]`). Each case
  is a diff built from exact edits to one file at a pinned commit, reviewed through
  `local-review` with exactly the arguments `pr-review.yml` renders from
  `[pr_automation.fallback]`. A defect is caught only when the verdict blocks and a finding is
  on the planted lines and names the defect's class; a control blocked or given a `blocking`
  finding is a false positive; a review with no verdict is counted apart by its outcome code.
  Each measurement is one digest-chained line in an append-only ledger, rendered into a page's
  generated block (`render --check` fails on drift). `status` holds the latest measurement to
  the declared floor -- recall's Wilson lower bound, the false-positive rate's Wilson upper
  bound, its age, the whole corpus, and the settings in force -- and exits 0, 1 or 3. A 2026-09-30
  audit found `think = "low"` passing every pull request the gate had blocked; no study had
  carried a known-true defect, so recall was never measured.
