* **gh:** the sovereign review can reach a verdict on a large pull request again. PR #1312's
  77-file review gave none: the model was free, read its first part in 145s, then reasoned
  past its 8,192-token reserve until a fixed 600s timeout cut it off, twice. The reserve is
  now the most the model may write (`num_predict`, default 16,384), each request's deadline
  scales with its size at the host's measured rates (`prompt_tokens_per_second`,
  `output_tokens_per_second`), and a review waits, bounded (`slot_wait_seconds`), for the
  model to come free before it is sent -- so a busy model (`model_busy`, retried) is told
  apart from one too slow for its input (`model_timeout`, named and not retried).
