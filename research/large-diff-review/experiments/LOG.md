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
- **18:40** Harness core written (`harness/client.py`, `cases.py`, `review.py`): slot
  etiquette (process table + server log, two clear reads 8 s apart, 30 s polls), a request
  that aborts only itself when a review client appears, an append-only request store
  keyed by the SHA-256 of the exact body (resume = skip what is recorded), deterministic
  check codes, production's chunker/excerpts/prompts/answer validation reused. Dry run
  (no model): host #1131 is 21/10/5/3 parts at k = 4/8/16/32k tokens; the contract
  request is ~30–37k tokens. Production's chunker refuses a context hunk larger than a
  part; the D arms use a `LenientChunker` that gives such a hunk a part of its own (over
  budget) instead — logged as a harness design choice. Sources are capped so a part never
  exceeds the window less the 16,384-token reserve.
- **18:42** Engineering observation (no quality outcome): production sizes `num_ctx` per
  request (`ContextSizer.num_ctx` = prompt tokens + reserve, so 65,482 for the canary's
  current case), and Ollama reloads the runner when `num_ctx` changes. The D arms use a
  constant `num_ctx` 65,536 so no request of this study forces a reload; the A arms keep
  production's sizing (they are production).
- **18:45** **Deliverable amendment (operator, 2026-10-01 22:09Z; changes deliverables,
  not hypotheses or decision rules).** Once a method is chosen, the experimentation must
  be reproducible, run monthly, and surfaced in `vibey doctor`, in two tiers: (1) a shipped,
  deterministic **full calibration** (class + interface, TOML config, pinned corpus
  manifest, seeds, needles; winner vs B0 plus the sweep that picks this host's operating
  point — part size, think, temperature/top_p, thinking and answer budgets, verifier N),
  writing an append-only calibration record with a host fingerprint and a per-host
  operating profile the review reads; run monthly on `vibey-local-vibey` by a workflow
  modelled on `minimum-specs.yml`, landing via PR; (2) a **`vibey doctor` "review
  calibration" section** (minutes): latest record, age, same-host check, FAIL when missing
  / older than a declared limit / other host or model digest, plus a smoke probe (one
  known needle + one control), and an opt-in `--calibrate-review` full run. The harness is
  built for that lift: deterministic seeds, pinned manifest, resumable, and every request
  record now carries `host` (fingerprint id: CPU, cores, memory, OS, Ollama version, model
  digests) and `model_digest`. Design goes in REPORT.md's implementation plan.
- **19:20** Waiting on the canary lane (17 of 41 cases at 18:16, ~12 min/case). Meanwhile:
  `+SA` and `+VER` implemented (`review.StaticAnalysis`, `review.Verifier`), and the
  deterministic **SA-only** arm run on the whole canary corpus (no model;
  `results/static_only.json`): a diagnostic counts when the change introduces it within
  ±2 lines of a changed range. ruff `--select ALL` + bandit flag **5/27** defects (all
  three `sql_injection` via S608/B608, two of three `swallowed_exception` via S112/B112)
  and **0/14** controls. Rule-to-class map fixed in `static_only.py` before the run.
- **18:40** EVIDENCE's findings arrived (`../evidence/findings.md`), before any
  experimental request. Pre-data amendments:
  1. Stage 1 runs the arms in the 5–20k-token region first (D8, D16, D4, then D16-BF4096,
     D32, A0, A1, A2): EVIDENCE's P(finish within 16,384) is 0.92 at 20k, 0.73 at 30k,
     0.53 at 40k, 0.36 at 50k, and only 6 past requests were under 20k.
  2. Every result is stratified by content type (code / tests / docs share of the part),
     since reasoning length depends on content independently of size (both p < 1e-6).
  3. The D arms' per-request deadline floor is raised from production's 600 s to 1,080 s
     (EVIDENCE: give each request ≥ 18 min; the #1316 formula barely covers a full-cap
     write past ~40k). Production arms keep production's own deadline.
  4. think=low is a documented negative control only (EVIDENCE: 213–330 tokens, passed all 8
     PRs, 4 of which default effort blocked) — D_k-low leaves Stage 2's halving and is run
     once, on round 1's cases, labelled as the negative control.
  5. Per-request slot wait is logged (`slot_wait_s`) and excluded from wall time; a fixed
     `num_ctx` per arm (already so) removes reload noise.
