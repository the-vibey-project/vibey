- **Fix:** a large pull request can get a sovereign verdict again, or an honest, specific
  reason why not. PR #1312's 77-file review gave none: the operator's host's Ollama log shows
  the model was free, read its first part (46,222 tokens) in 145s, then wrote ~9,950 tokens
  of reasoning -- past an 8,192-token reserve nothing enforced -- until a fixed 600s cut it
  off; the retry, identical at temperature 0, did the same (10,017 tokens). Now the
  reasoning reserve is sent as `num_predict`, so it is the most the model may write, and its
  default is 16,384 (that log's reviews finished at up to 11,832 tokens). Each request's
  deadline scales with its size at the host's measured `prompt_tokens_per_second` (200) and
  `output_tokens_per_second` (20), never under `timeout_seconds`. Before each request a
  one-token probe at the same window waits, up to `slot_wait_seconds` (900), for the model
  to come free, so a review queued behind another client is coded `model_busy` (new) and
  retried, while a request that started on a free model and still ran past its deadline is
  `model_timeout`, says why, and is not retried. All three are `[pr_automation.fallback]`
  keys, rendered into `pr-review.yml`; `0` for them restores the old behaviour.
