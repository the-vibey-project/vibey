- **Feature:** `vibey-gh review-canary` measures in shards, so the weekly canary runs on
  GitHub-hosted runners only. `run --shard I/N --out FILE` reviews the cases whose place in
  the corpus is `I` modulo `N` and writes what it heard; `merge FILE...` refuses unless the
  shards cover every case exactly once under one corpus, commit, model and set of settings,
  then records the same ledger line an unsharded run would; `plan` names the model and one
  `I/N` per `[pr_automation.review_canary] shards`. `prompt_tokens_per_second` and
  `output_tokens_per_second` in the same table set the canary's deadline rates for the
  hardware it runs on, leaving `[pr_automation.fallback]` unchanged. An unsharded `run` is
  unchanged.
