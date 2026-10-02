# Evidence: what the existing review data establishes

Cutoff: Ollama logs to 2026-10-01T21:45:14Z; GitHub data fetched ~21:40–21:55Z.
No request was sent to the local model by this track. Code and data: `analysis/`, `dataset-*.jsonl`,
`figures/`, `raw/` (Ollama log snapshot with sha256 manifest; GitHub runs, jobs, logs, artifacts, diffs).

Note (main session): the "unidentified host client" below — 127.0.0.1, ~25k-token review prompts from
16:38 local on 2026-10-01 — is most likely the review-canary lane (`lane/review-canary`), which was
running its 41-case corpus on the model at that time (14/41 done at 17:40 local, per the experiment
track). Its requests remain excluded from the thresholds below.

## Coverage
- Ollama: 6 files read in full (149,598 lines), 2026-09-27 06:13Z → 2026-10-01 21:45Z; 0 unparseable.
  691 requests reached a model slot (688 joined to their access line; 3 not, incl. 1 in flight at the
  snapshot). 2,163 access lines never reached a slot (2,066 cloud `/api/codex/v1/responses`) are kept as
  `no_task`. Gaps in the log: 09-27 06:23–11:01Z, 09-28 14:52–16:23Z, 09-30 20:26–23:54Z. No older log.
- GitHub: 559 `pr-review.yml` runs (09-21 → 10-01); 180 completed Sovereign diff review jobs (50 logs
  404, kept `log_available=false`); 125 verdict/outcome artifacts; 108 (PR, head) diffs fetched as
  `pr.base.sha...head_sha` compares, matching logged character counts on all 5 jobs that state them.
  (A first pass against today's develop gave wrong diffs after history rewrite; deleted.)
- Provenance: all 134 `::1` requests fall inside a Sovereign job's review step (CI); `127.0.0.1` are
  host runs (09-30/10-01 studies, and the unidentified client above). Of 105 CI jobs inside log
  coverage, 82 join to requests; the other 23 sent none (18 refused for size: 13 `diff_exceeds_window`,
  5 `chunk_budget_exceeded`; 5 cancelled before review). 75 jobs before 09-27 cannot be joined.

## Population and method
145 gpt-oss:20b PR-review requests at default/medium effort (125 CI + 20 earlier think/source-context
study runs); prompts 18,252–57,227 tokens (median 35,368); 68 stopped naturally, 77 censored (cancelled,
timed out, hit the cap, or filled the context). Censored (survival) estimates, log-normal AFT best fit;
CIs from a cluster bootstrap by PR (80 PRs).

## Reasoning length
- Natural stops only (biased low, n=68): median 2,614 tokens (CI 1,250–3,517), p90 7,534, max 11,833.
- All 145 with censoring: median need 9,340 tokens; P(finish within 16,384) = 0.58 (0.48–0.70).
- Grows steeply with prompt size: AFT slope on log(prompt) 2.95 (CI 1.84–4.20) — roughly prompt³ here.
- Content matters independently of size: on 47 single-request CI reviews, test-dominated diffs needed a
  median 3,825 tokens vs 995 for docs; with both log(prompt) and code+test share in the model, both are
  large (2.37 and 2.39, each p < 1e-6). A small part of code and tests can still reason long.

## P(finish within 16,384 output tokens) vs prompt size

| prompt tokens | AFT (95% CI) | Kaplan–Meier bins |
|---|---|---|
| 20k | 0.92 (0.84–0.98) | 20–30k: 0.79 (0.63–0.91), n=38 |
| 30k | 0.73 (0.64–0.85) | 30–40k: 0.55 (0.41–0.70), n=53 |
| 40k | 0.53 (0.39–0.68) | 40k+: 0.24 (0.13–0.41), n=48 |
| 50k | 0.36 (0.21–0.56) | |

- Largest prompt with P ≥ 0.95: ~17,000 tokens (CI 12,000–23,000) — partly extrapolated (only 6
  requests under 20k).
- Finishing inside the deadline then in force: 0.95 only up to ~15k prompt tokens (0.88 at 20k, 0.31 at
  40k).
- Sensitivity: CI-only 0.94 / 0.73 / 0.47 at 20k / 30k / 40k. Adding host runs of unknown settings
  flattens the curve; not used for thresholds. KM bins are upper bounds (no request in any bin was still
  running past 16,384 tokens).

## Rates and time
- Prompt eval: 580 / 459 / 379 / 324 / 282 tok/s at 10k / 20k / 30k / 40k / 50k (n=256, R² 0.97). The
  lane's declared 200 tok/s is conservative.
- Generation: 28.6 / 23.4 / 21.4 / 19.6 / 18.2 tok/s at context 1k / 20k / 30k / 40k / 50k (n=138);
  varies up to 2× with host state (daily medians 31.0, 29.8, 18.0, 22.4; per request 12–34). The lane's
  declared 20 tok/s is optimistic past ~38k context.
- Model reload: median 4.8 s, p90 8.5 s; 72% of CI requests reloaded (each asks for a different num_ctx).
- Time model (load + read + write) predicts the 68 natural stops within 14.9% median absolute error
  (p90 21%).
- Minutes per request: 20k → 2.2 at median need / 13.4 to write the full cap; 30k → 6.5 / 15.1;
  40k → 15.4 / 17.0. #1317 part 3 matches (34,774-token prompt, 16,384 written, 883 s).
- Reasoning text: 3.9–4.8 chars/token (mean 4.3, n=4).
- #1316 deadline (prompt/200 + 16,384/20) margin over a full-cap write at measured rates: about +33 s at
  35k, +2 s at 40k, −33 s at 45k; at 15 tok/s every size overruns. Past ~40k a request that should end
  `done_reason=length` ends `model_timeout` instead.

## Contention
CI wait for the slot (n=125): median 3.8 s, p90 102 s, p95 294 s, p99 549 s; 14.4% waited > 60 s
(CI 9.3–21.6%). 25 arrived while a host client's request ran; none waited behind another CI request.
#1316's one-token slot probes waited 28–593 s. No model-load failures hit CI.

## #1316 before/after (too few cases to judge)
Verdict rate: before 46/88 jobs that sent a request (0.52), after 3/5 (0.60); Fisher p = 1.0. After the
merge: 5 natural stops, 2 cap hits (#1317 at 34.8k, #1321 at 37.2k), 1 cut at 600 s (#1316's own run).
The change turned some timeouts into cap hits, as designed — not evidence of a better verdict rate.

## All 180 CI jobs
reviewed 49 · cancelled 65 · model_timeout 33 · diff_exceeds_window 14 · answer_unusable 8 (all
09-24) · chunk_budget_exceeded 5 · answer_incomplete 2 · job_failed_before_review 2 · prompt_truncated 1 ·
empty_diff 1.

## Effort
At think=low the model wrote only 213–330 tokens and passed all 8 PRs, including 4 that default effort
blocked — confirms the rubber-stamp finding; lowering effort is not a fix.

## Thresholds for the experiment track
1. Keep each request ≤ ~15–17k prompt tokens for ≥ 95% completion within 16,384 output tokens (~92% at
   20k). The < 20k region is barely measured: measure it first.
2. Stratify by content type: code/tests reason ~4× longer than docs at equal size.
3. Plan on ~20 tok/s generation from a 40k start; record the host's actual rate per run (12–33 observed).
   Prompt eval 300–450 tok/s.
4. Expect 2–7 min at median need for 20–30k prompts and 13–17 min to write the full cap; give each
   request a deadline of at least 18 min.
5. Keep the host otherwise idle during runs, or log each request's queue wait so it can be subtracted.

## Not established
Causality (that splitting lowers per-part need — prompt size, content and PR identity are confounded);
behaviour at 5–20k prompts under review settings; reasoning vs answer tokens (the log gives their sum);
verdict correctness; what `think ''` maps to inside Ollama (treated ≈ medium); CI jobs before 09-27,
the 50 with missing logs, and the unidentified client's settings.

## Inference caveats
`length` is inferred when exactly 2048/4096/8192/16384 tokens were written, `length_ctx` when prompt plus
output filled the context; 256 is not treated as a cap (think=low stopped there naturally twice). The
earlier study's timings include up to 565 s of waiting behind CI that night.
