- **Fix:** a `review-canary` measurement whose reviews were resumed from a `--work` file now
  records how many (`reused_reviews`) and when the reviews that carry a time ran
  (`reviewed_between`), and the rendered block says so -- before, its start and finish times
  were only when it was scored and recorded.
