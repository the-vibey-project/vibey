- **Feature:** the autonomy scorecard. How far vibey is from full autonomy is now a weekly
  measurement, not a paragraph: `scripts/autonomy_scorecard.py` judges each declared stage of
  the delivery loop (DESIGN, BUILD, the paid engines, REVIEW, the pull-request review and its
  trustworthiness, approval, merge, promotion and release, CI, the queue reaching DONE) from
  the forge (`gh`), the review canary (`vibey-gh review-canary status`), the code and the
  local queue (read only), against the thresholds and reasons declared in
  `scripts/autonomy_scorecard.toml`. Each measurement is appended to the digest-chained record
  `docs/architecture/evidence/autonomy-scorecard.jsonl`; a source a run cannot read keeps its
  last values, marked stale with their date, then shows as unknown. The new page
  [How far vibey is from full autonomy](docs/reference/autonomy.md), the README's and the
  landing page's Status summaries and the paper's scorecard table are generated from the
  latest line, `check` fails CI on any drift, and `autonomy-scorecard.yml` refreshes it every
  Thursday through a pull request.
