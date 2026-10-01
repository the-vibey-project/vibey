# Preregistration — a sovereign review method that reaches a verdict on large diffs

- **Registered:** 2026-10-01, before any quality outcome (recall, false positive) of any
  arm below was observed. Committed to `research/large-diff-review` and pushed before the
  first experimental request; the commit that adds this file is the registration.
- **Track:** EXPERIMENT (sibling tracks PRIOR-ART and EVIDENCE feed in; see §10).
- **Code under study:** `src/vibey_tools/gh/vibey_gh/local_review.py` at `3293528`
  (develop after #1325), configuration `[pr_automation.fallback]` in `.vibey-gh.toml`.
- **Host:** Apple M5, 10 cores, 24 GB, Ollama 0.35.0, `gpt-oss:20b` (MXFP4), one slot
  (`n_slots = 1`), shared with live pull-request reviews and the review-canary lane.

What was already known when this was written (and is therefore not a finding of this
study): PR #1317's third part wrote 78,418 reasoning characters and no answer
(`done_reason=length`, 39.5 min); PR #1312 timed out mid-reasoning; small diffs complete;
`think = "low"` was found to pass every PR the gate had blocked (2026-09-30 audit); a
large paper diff's only finding was a false positive. Seen while orienting, before
registration (timing only, no quality outcome): the production request for a
whole-scope review carries `README.md` and `docs/index.md` (85,857 characters, ~29k
tokens) in **every** part; the canary lane's in-flight cases read ~37k-token prompts at
~280 tok/s and generate at ~12.4 tok/s at that context; the production check code opens
the system prompt, so no two requests share a cacheable prefix.

## 1. Question (PICO)

- **Population:** pull-request diffs of this repository that the production sovereign
  review cannot take in one request ("large": `len(diff)` exceeds the production
  `SovereignReview.room(documents, part=False)` at the PR's merge commit), from PRs merged
  into `develop` 2026-09-25..2026-10-01, excluding release merges and promotions to `main`
  (45 diffs; `corpus/hosts.json`). Secondary population: the small single-file diffs of
  the review-canary corpus (`docs/architecture/evidence/review-canary/corpus.toml`, pin
  `2b17eb7`, 27 planted defects in 9 classes, 14 controls).
- **Intervention:** candidate review methods (§3) on the same model and host.
- **Comparator:** B0, the production method, called through the real `local_review` code
  path with the production settings.
- **Outcomes:** verdict rate; recall on planted defects; false-positive rate on clean
  changes; p50/p95 wall time; tokens (§5).

## 2. Hypotheses

For each candidate method M against B0:

- **H1 (verdict).** H0: M's verdict rate on large diffs ≤ B0's. H1: greater.
- **H2 (recall, small diffs).** H0: recall(M) − recall(B0) ≤ −δ (inferior). H1: > −δ
  (non-inferior), δ = 0.15.
- **H3 (false positives).** H0: FP(M) − FP(B0) ≥ +δ_FP. H1: < +δ_FP, δ_FP = 0.15.
- **H4 (time).** M's p95 wall time on large diffs ≤ T_cap = 120 min (the job limit is 360).

Mechanism hypotheses, each tested because a method depends on it:

- **Hm1 (runaway reasoning).** No-verdict requests are dominated by reasoning that does not
  converge (`done_reason=length` with no answer, or a deadline hit mid-analysis), and its
  frequency rises with prompt size. Measured as P(no answer) by prompt-token band.
- **Hm2 (greedy loops).** At temperature 0 the unfinished reasoning is repetitive
  (repeated-8-gram fraction of the analysis text higher than in finished reasoning);
  sampling at the model's own default (temperature 1.0) finishes more often.
- **Hm3 (forcing preserves judgment).** Ending the analysis channel at R tokens and
  forcing the final channel yields a schema-valid verdict on ≥ 99% of requests, and
  recall at R ≥ 4096 is non-inferior to unforced requests that finish on their own.
- **Hm4 (compounding false positives).** A method that splits a diff into m parts has a
  diff-level FP of 1 − Π(1 − fp_part); per-part FP must therefore be much lower than the
  diff-level target, which is what a verify pass is for.

## 3. Arms

Every arm is a deterministic map from a diff to a set of model requests plus a reduce
rule. Defaults unless an arm says otherwise: `gpt-oss:20b`, think unset ("Reasoning:
medium" in the harmony template — what production sends), temperature 0, `num_predict`
16,384, deadlines by the production formula (prompt/200 + output/20 s, floor 600 s),
integrity check codes as production seals them (made deterministic per request content in
the harness so that identical requests are identical, §6).

| Arm | What it is |
|---|---|
| **A0 = B0** | Production: `SovereignReview.run` via `local_review.review(argv)` with the argv `ReviewCanary.argv` renders from `[pr_automation.fallback]` (scope full, documents, sources, `max_chunks` 6, slot wait, retries). |
| **A1** | A0 + budget forcing (BF, below) at R = 4096 on every part. |
| **A2** | A0 at temperature 1.0, top_p 1.0, seed 42 (the model's own default sampling). |
| **D_k** | Decoupled small parts. The diff is cut by production's own `DiffChunker` to parts of at most k diff tokens (k ∈ {4k, 8k, 16k, 32k}, at 3 chars/token); each part is one **defect request**: the diff-half rules and schema (findings carry an optional `line`), plus that part's own reference sources excerpted by production's `SourceContext`, at most k tokens, and **no documents**. Plus ONE **contract request** per diff: the whole-review system prompt and schema, the declared documents, and a digest of the diff (every file with its +/− counts, then the prose sections in full and code sections' hunk headers, to a 16k-token budget). Reduce: findings are the union; `pass` is the AND of every request; any request without a verdict ⇒ no verdict for the diff (strict). |
| **D_k-BF_R** | D_k with budget forcing at R ∈ {2048, 4096, 8192}. |
| **D_k-low / D_k-high** | D_k at think "low" / "high". |
| **+TRI** | Deterministic triage before partitioning (harness `Triage`): sections classed binary, rename, deletion, generated (lockfiles, minified, maps, coverage, dist/build, vendored, images, self-declared generated) are summarised one line each and not sent to a defect request; `docs` (prose) go to the contract request only; `code` (everything else, workflows and config included) is partitioned. |
| **+SA** | Static analysis first: `ruff check --select ALL` and `bandit` on the post-change text of every changed Python file; diagnostics on changed lines are added to the part's prompt as reference. |
| **+VER** | Generate→verify: every finding of a defect request goes to one focused request (the finding, its hunk, ±40 lines of the post-change file) asking whether the cited line exists and the defect is real; only confirmed findings survive, and a part whose findings are all refuted passes. |
| **ALT_m** | D_k (the k Stage 1 selects) with model m ∈ {qwen3:14b, qwen2.5-coder:14b, gemma4:26b}. |
| **SM** | qwen2.5-coder:1.5b reads each hunk and flags risky ones; gpt-oss runs D_k only on parts holding a flagged hunk; unflagged parts pass. |
| **Combinations** | Of Stage 2's survivors, at most three, named in LOG.md before they run. |

**Budget forcing (BF_R).** Request 1 is the arm's normal `/api/chat` request with
`num_predict` = R. If it ends `done_reason=stop` with a complete answer, that is the
answer. Otherwise request 2 is `/api/generate` with `raw: true`: the conversation rendered
exactly as the model's harmony template renders it (verified against `ollama show
gpt-oss:20b --template` and by equal `prompt_eval_count`), then
`<|start|>assistant<|channel|>analysis<|message|>{request 1's reasoning}<|end|><|start|>assistant<|channel|>final<|message|>`,
with the same `format` schema and `num_predict` 4096. The tokens are taken from the
template, not assumed; if PRIOR-ART supplies a different control that is more direct, it
is added as a separate arm, not substituted.

## 4. Corpus

- **Hosts** (large real diffs): `git diff -M <merge>^ <merge>` of each eligible PR, with
  the documents and every changed file's text at the merge commit (`corpus/hosts.json`:
  45 eligible; split dev 22 / holdout 23 by `random.Random(20261001)`).
- **Needles:** each of the 27 canary defects is a single-file diff built exactly as the
  canary builds it. A needle case is a host diff with one needle's file section inserted
  before the first section whose cumulative offset reaches a fraction f of the host
  (early f = 0.05, middle 0.50, late 0.95); the needle file's post-change text joins the
  host's reference sources. A needle whose path the host already changes is skipped for
  that host in favour of the next in order. One needle per case.
- **Controls:** the host diff itself (a merged PR, assumed clean — a threat, §9; blocking
  findings on controls are kept verbatim for adjudication) and the 14 canary controls.
- **Matching rule:** the canary's `FindingMatcher` unchanged (located on the needle file
  by `line` ± 3 or by quoting an anchor, AND a class keyword), and its outcome labels:
  CAUGHT / MISSED / CLEAN / FALSE_POSITIVE / NO_VERDICT. Additionally recorded: ESCAPE =
  a defect case whose verdict is an explicit pass.
- **Split of needles:** one per class to development (`selection.json` `dev_needles`, 9),
  two per class held out (`holdout_needles`, 18).
- **Selections** (`corpus/selection.json`, seeds 20261002–20261004): screening hosts S1 =
  #1131, #1161, #1250, #1282 (dev, ≤ 260k chars); halving hosts S2 = S1 + #1155, #1305;
  confirmation hosts (holdout) = #1121, #1137, #1166, #1170, #1249, #1251, #1252, #1259,
  #1307, #1313, #1317, #1323. Holdout hosts and holdout needles are not reviewed by any arm
  until Stage 3.

## 5. Outcomes and analysis

- **Verdict:** every request the arm makes for the diff returns a complete,
  schema-valid answer echoing both check codes, and the total wall time (excluding time
  waiting for another client's request) is ≤ T_cap = 120 min.
- **Recall** = CAUGHT / (defect cases with a verdict) — the canary's definition.
  **Effective recall** = CAUGHT / all defect cases (no verdict counts as not caught).
  **Escape rate** = ESCAPE / all defect cases.
- **FP rate** = FALSE_POSITIVE / (controls with a verdict) — the canary's definition
  (blocked, or any `blocking` finding).
- **Time:** p50/p95 wall time per diff, and per 10k diff tokens; tokens read and written.
- Every proportion with a Wilson 95% interval. Differences: Newcombe's hybrid score
  interval (independent samples) or Newcombe's method 10 (paired, same cases). Reported
  per defect class and per needle position. All arms reported, failures included.
- **Part-level composition.** Parts of an arm are independent requests; a needle case
  differs from its host only in the part holding the needle. A request is identified by
  the SHA-256 of its exact body; identical bodies are answered once and the diff-level
  outcome is composed from the requests' results. Valid only if identical requests give
  identical answers: measured by replicating ≥ 10% of requests (§6), and reported.

## 6. Procedure and stages

0. **Feasibility (no quality outcome read):** verify the harmony rendering for BF (equal
   `prompt_eval_count`), the prompt cache, and request timing on the canary's small diffs'
   *timing only*.
1. **Screening — verdict and time.** Arms A0, A1, A2, D4, D8, D16, D32, D16-BF4096 on the
   four S1 hosts (clean). Every part of every D arm is run (needed for composition).
   Rule: an arm is dropped when its verdict count on S1 gives a Wilson upper bound < 0.95
   (i.e. ≥ 1 failure of 4 drops it — since the 95% target needs near-certain parts), or
   its median time exceeds T_cap. Of the D_k that survive, the two fastest k go on.
2. **Successive halving — recall and FP**, development data only: needle parts of the 9
   dev needles × 2 positions on the S2 hosts (18 defect cases) and the S2 hosts' clean
   parts (FP per part, composed to FP per diff by Hm4). Round 1: every surviving and
   Stage-2 arm (BF_R sweep, low/high, +TRI, +SA, +VER, ALT, SM) on half the cases; the
   better half by (recall − composed FP), ties by time, go to round 2 on all cases. The
   winner, and at most three combinations of round-2 survivors, are named in LOG.md
   before Stage 3.
3. **Confirmation.** The winner and A0 on the 12 confirmation hosts (clean), each with
   three holdout needles at early/middle/late (36 defect cases), and on the whole canary
   corpus (27 + 14, paired with A0). Nothing in Stage 3 changes the method.
- **Replication:** ≥ 10% of Stage 2–3 requests, chosen by seed, re-run with the cache
   bypassed; agreement of verdict and of CAUGHT reported.
- **Model etiquette:** before every request the harness checks `/api/ps` and the server
  log for an in-flight request, and the process table for any `local-review` or
  `review-canary` process; it waits (30 s polls) until all are clear. If one appears while
  the harness's own request runs, the harness aborts **its own** request (never
  another's), records it as yielded (not a result), and re-queues it. Models are swapped
  only when no other client is active, and runs are batched per model.

## 7. Decision rules

M **works** when, on Stage 3:

1. verdict rate on the 48 confirmation diffs (12 hosts + 36 needle cases) ≥ 0.95 as a
   point estimate, with its Wilson lower bound reported (and ≥ 0.80, or the claim is
   "inconclusive"), and every diff within T_cap;
2. recall on the canary's 27 small defects non-inferior to A0: the lower bound of the
   paired 95% interval of recall(M) − recall(A0) > −0.15;
3. FP not raised: the upper bound of the 95% interval of FP(M) − FP(A0) on the canary's
   14 controls < +0.15, and FP(M) on the 12 large controls reported with its interval.

Each criterion is reported PASS / FAIL / INCONCLUSIVE (interval straddles the margin).
Large-diff recall of M is reported against A0's effective recall on the same 36 cases.

## 8. Sample size and precision (a priori)

The binding constraint is one model slot at ~12–22 output tok/s; sizes are chosen for
precision, and the precision they buy is stated rather than overstated:

- 48 confirmation diffs, all with a verdict ⇒ Wilson 95% lower bound 0.926 (47/48 ⇒
  0.891). The 36 needle diffs share 12 hosts, so a host-clustered bound is also reported
  (12/12 ⇒ 0.757).
- Recall on 27 small defects at p ≈ 0.6: Wilson half-width ≈ 0.18; the paired difference's
  half-width ≈ 0.12–0.20 depending on discordance. A true difference of 0 is declared
  non-inferior at δ = 0.15 only if discordant pairs are few; INCONCLUSIVE is a likely,
  honest outcome.
- FP on 14 controls: 0/14 ⇒ upper bound 0.215; 2/14 ⇒ [0.040, 0.399].
- Screening with 4 hosts can only prune grossly failing arms; that is all it is used for.
- Estimated model time: Stage 1 ≈ 12 h, Stage 2 ≈ 12 h, Stage 3 ≈ 15 h.

## 9. Threats, stated in advance

Merged PRs are assumed clean (some may hold real defects: blocking findings on controls
are adjudicated by hand and both figures reported). Needles are canary defects spliced in
as an extra file, not edits inside the host's own hunks; they come from one author's
corpus. The keyword matcher is lexical. One host, one quantisation, one Ollama version.
Temperature 0 is near- but not fully deterministic (measured). Development and
confirmation hosts come from one week of one repository.

## 10. Deviations

Any change after registration — an arm added on PRIOR-ART's or EVIDENCE's advice, a
sample cut for time, a bug fix in the harness — is logged in `LOG.md` with its time and
reason before the data it affects is looked at, and listed in REPORT.md's Methods.
