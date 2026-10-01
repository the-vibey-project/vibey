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
- **18:12** PRIOR-ART's findings arrived (`../prior-art/findings.md`), before any
  experimental request. Pre-data amendments, adopted now (PREREGISTRATION §10):
  1. **Mechanism replay (Hm2):** the #1312 part-1 request (dev host) and the #1317 part-3
     request replayed at T=0 and at T=1.0/top_p 1.0 × 5 seeds; logged: eval_count,
     done_reason, wall time, and PRIOR-ART's loop metric (a ≥200-char substring repeating
     ≥3× in the last ~4k chars of the thinking) beside the registered repeated-8-gram
     fraction. #1317 is a holdout host: its replay is a **mechanism** measurement of the
     production request only — completion and loop metrics are read, its verdict content
     is not read or scored, and no arm is tuned on it. Declared here so it can be checked.
  2. **Budget forcing:** primary mechanism becomes PRIOR-ART's `/api/chat` prefill — phase 2
     repeats the messages plus an assistant message carrying the truncated thinking, a
     short budget note, and a NON-EMPTY content prefix, same think level. The registered
     raw `/api/generate` route is kept as a second variant. Both are verified live in
     Stage 0 (does `format` still constrain a prefilled final channel? is the prefix KV
     reused — `prompt_eval_count` in phase 2?) before either is used for an outcome.
     Budget sweep R ∈ {4096, 8192, 12288} replaces {2048, 4096, 8192}; answer cap 2,048.
  3. **Forced-verdict fidelity (Hm3):** requests that finish naturally are re-run with R
     below their natural length and the two verdicts compared (agreement, CAUGHT kept).
  4. **Context factor (Stage 2):** reference context = none / changed region with its
     enclosing function (production `SourceContext.excerpt`) / whole file, since one
     study found whole-file context lowered detection in 8/8 models.
  5. **Verifier (+VER):** conclusion-first TRUE/FALSE/UNCERTAIN, N = 3 samples at T=1.0,
     a finding kept at ≥ 2/3 TRUE; UNCERTAIN kept (a human looks).
  6. **Never low for verdicts** is PRIOR-ART's advice; D_k-low stays in Stage 2 because
     small parts may change that, and its recall is the test.
  7. Secondary matcher sensitivity: file ± 5 lines + class keyword, beside the canary's ± 3.
