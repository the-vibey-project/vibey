# Lab notebook — EXPERIMENT track

Times are America/New_York (host clock). Newest last. Every entry says what was done,
what was seen, and what it changed.

## 2026-10-01

- **17:40** Oriented. Worktree at `3293528` (develop after #1325, the review canary).
  Production settings read through `ReviewCanary.settings`: scope full (no paid review),
  think unset, window 65,536, reserve 16,384, 3 chars/token, `max_chunks` 6, sources on,
  deadline rates 200/20 tok/s, slot wait 900 s, retries 1. The model was busy: the
  review-canary lane's smoke run (`review-canary run --no-record`) was mid-corpus, 14 of
  41 cases done, one `model_timeout`. Per the etiquette no request was sent.
- **17:45** Timing facts seen in the server log (no quality outcome): a 37,577-token
  prompt read at ~277 tok/s overall (~650 tok/s in its first 2.5k tokens); generation at
  ~12.4 tok/s at that context. `README.md` + `docs/index.md` are 85,857 chars and ride in
  every production part. The prompt cache is on in Ollama 0.35's runner, but production
  opens every system prompt with a fresh random check code.
- **17:50** Harmony template read (`ollama show gpt-oss:20b --template`): think unset ⇒
  "Reasoning: medium"; an assistant message with thinking only is rendered
  `<|start|>assistant<|channel|>analysis<|message|>…` with no `<|end|>` (prefill), one
  with content renders the analysis closed and opens `<|channel|>final<|message|>`. The
  model's own default temperature is 1.
- **17:52** Corpus: all 140 PRs merged 2026-09-25..10-01 listed; 133 into develop; diffs
  built from the squash merge commits with `git diff -M`; 45 are "large" by the
  production room rule (#1290's merge commit is not in the clone — excluded). Split and
  selections drawn by seed (`corpus/selection.json`).
- **18:05** PREREGISTRATION.md written and committed before any experimental request.
