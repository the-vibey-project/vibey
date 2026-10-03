# Completion prompt: finishing the large-diff sovereign review, and shipping what it finds

You are taking over a running experiment in the vibey repository
(`the-vibey-project/vibey`). Your job is to carry it through to its end, then put the
method it selects into production, so that vibey's sovereign pull-request review
reaches a verdict on large diffs. This prompt describes where the work stands, what
"done" means, and every step between the two. Read all of it before you act.

**Cutoff.** Every status claim below was read at 2026-10-03 18:10 EDT, from the live
store at `~/git/vibey-storm/research-large-diff-review/research/large-diff-review/experiments/results/`,
from `develop` at `3062bf17f` (the 4.0.0 release commit), and from the forge. Treat
each claim as true at that cutoff only (sub-doctrine 10.f). Re-read the store before
you rely on any number in this prompt.

---

## 0. Rules that bind this work

These are not suggestions. Each one has already been broken once on this project,
and the break cost real time.

1. **The preregistration binds.** `experiments/PREREGISTRATION.md` (committed
   2026-10-01, before any outcome was seen) fixes the question, the arms, the corpus,
   the stages and the decision rules. You may not change a method, a threshold or a
   sample after you have seen data it affects. Any deviation goes into `LOG.md`, with
   its time and reason, **before** you look at the data it touches. It is then listed
   in REPORT.md's Methods. A deviation logged afterwards is a fabricated method.
2. **Nothing is evidence that the store does not hold.** Every number you report comes
   from `harness/analyze.py`, run against `results/` (or the committed snapshot `data/`).
   You name the function and the time. Count requests only through
   `analyze.py requests`, never by hand. (A hand count was wrong once; see LOG 00:12,
   10-02.)
3. **Live reviews outrank the experiment.** The model has one slot on one host (Apple
   M5, 24 GB, Ollama, `gpt-oss:20b`), shared with the CI review lane. The CI runner
   (`vibey-local-vibey`) runs **inside Docker**, so `ps` cannot see it. The harness's
   etiquette (`client.Model` / `Etiquette.connections()`) watches TCP clients on port
   11434. It yields its own request, and never anyone else's. Do not weaken this, and
   do not run a second harness process: `results/.model.lock` is the mutex.
4. **The data is append-only.** Never rewrite `results/*.jsonl`. You void a record by
   appending to `invalidations.jsonl`, keyed by (key, t_start), and a diff row by
   tombstoning its line number in `void_rows.jsonl`. A transport failure is cached like
   any other answer, so voiding one takes **both** files (LOG 14:59, 10-03).
5. **Work outlives the machine (10.h).** Work in progress stays under
   `~/git/vibey-storm`, never on volatile storage (the storm tools refuse it with exit 78). `harness/push_snapshot.sh` snapshots `results/` →
   `data/`, commits `research/` only, merges `origin/develop`, and pushes through the
   storm push gate. Run it every 30–45 minutes while anything runs. It opens the next
   numbered `research/large-diff-review-N` branch and draft PR when the previous one has
   merged. It never forces, never uses `--no-verify`, and never merges.
6. **Bounded by a gate, never by judgement (12.d).** Code reaches `develop` only as a
   pull request through the merge train. You never approve your own change, never push
   to a protected branch, and never route around a check. The operator often merges
   mid-review, so keep every fix a commit that can be cherry-picked on its own.
7. **Pins must be ancestors of `origin/develop`.** Promotion rebase-merges `develop`
   into `main`, and the realign then rewrites `develop`'s SHAs. A pin to a commit that
   exists only on a side branch, or only in the old history, breaks every fresh clone.
   This happened on 2026-10-03: the review-canary corpus pin `2b17eb7` was orphaned and
   is now `0f88412`, the same tree (see §3.4).
8. **Code lives in classes with an interface beside each (ADR-0016).** Keep `domain/`
   pure. Everything configurable is declared in TOML (12.c). The family is dogfooded:
   reuse `vibey_bootstrap` retry, `vibey_gh.slots`' `DeviceFingerprint` and ADR-0058's
   calibration before writing anything new (10.e).

---

## 1. The problem being solved

vibey's sovereign review (`vibey-gh local-review`, run by the `review-sovereign` job of
`.github/workflows/pr-review.yml` on the self-hosted runner) reaches verdicts on small
diffs and **fails on large ones**:

- #1317's third part wrote 78,418 reasoning characters and no answer
  (`done_reason=length`, 39.5 min).
- #1312 timed out mid-reasoning.
- Diffs that do not fit are refused outright (`diff_exceeds_window`,
  `chunk_budget_exceeded`).

With `paid_review = false` (the sovereign default, 8.a), the gate succeeds only on a
whole verdict that passes. So every large PR currently ends at "a human is needed".

**The question (PICO, PREREGISTRATION §1):** for diffs too large for one production
request, which review method reaches a verdict on ≥ 95% of them within a T_cap of
120 min, with no loss of recall on planted defects (non-inferior at δ = 0.15) and no
rise in false positives, compared with production (A0 = B0)?

---

## 2. What is already established (do not re-derive it)

- **The mechanism is greedy decoding, not size alone.**
  - On the identical request (#1131, D8 part 1, 13,894 prompt tokens), temperature 0 ran
    to the 16,384-token cap in 697 s with no answer. 86% of its word 8-grams repeat, and
    it loops on "This is obviously not helpful. Let's step back."
  - At T = 1.0 / top_p 1.0 / seed 42 (the model's own default sampling) the same request
    answered in 368 tokens, 39 s.
  - Production sends `temperature: 0` explicitly (`vg/local_review.py:1110`, the slot
    probe at `:776`, triage at `:2234`), so the default is the defect.
- **T = 1 brings three rarer failures, and budget forcing repairs all of them:**
  - the answer escapes the `format` grammar (bare check codes, then off-schema keys);
  - the turn ends in the analysis channel with an empty answer;
  - (rarely) a run to the cap even at T = 1.

  **Budget forcing** works like this:
  1. Phase 1 is the normal request with `num_predict = R`.
  2. If phase 1 ends without a usable answer (`length`, `answer_incomplete`,
     `answer_unusable`, or an empty answer), phase 2 repeats the messages plus an
     assistant message carrying the phase-1 reasoning, a one-line budget note, and
     content `" "`, with `format` kept.

  Stage 0 verified it: the harmony rendering is exact (687 = 687 prompt tokens), the
  grammar still constrains a prefilled final channel, and the KV of prompt + reasoning
  is reused, so phase 2 costs about 4 s.
- **Production defeats its own prompt cache.** It sizes `num_ctx` per request
  (`fit.py:730-732`), so the runner reloads on about 72% of CI requests. It also opens
  every system prompt with a fresh random check code (`CANARY_HEAD`,
  `local_review.py:233-239`), so no two requests share a prefix.
- **The schema order makes the model commit to `pass` before it writes findings.**
  - `REVIEW_SCHEMA` (`local_review.py:77-97`) and `review_contract.DEFAULT_FIELD_SCHEMAS`
    (`review_contract.py:133-140`) put `pass` first and `findings` last, and constrained
    decoding writes properties in that order.
  - The canary lane saw `pass: true` verdicts whose own summary named the planted
    defect, with an empty findings list.
  - +CONS (a findings-decide reduce) recovers nothing for that reason. +FF
    (findings-first order) is the arm that tests it.
- **The deterministic baseline:** ruff `--select ALL` + bandit alone catch 5/27 canary
  defects (3/3 SQL injection, 2/3 swallowed exception) with 0/14 false positives.
- **Sibling tracks** (cite them; do not redo them):
  - `../prior-art/findings.md`: greedy decoding loops gpt-oss chain-of-thought; Ollama
    prefill can force an answer; smaller units and a separate verify step help; whole-file
    context lowered detection in 8/8 models.
  - `../evidence/findings.md`: over 145 past requests, P(finish within 16,384 tokens)
    falls from 0.92 at 20k prompt tokens to 0.36 at 50k; content type matters
    independently of size.

### Stage 1 (screening, complete 2026-10-02 11:10; 4 dev hosts, 161–225k chars)

- **Kept** (a verdict on all 4 hosts):
  - A1 (production + forcing at 4,096), p50 18.4 min;
  - A2 (production at T = 1), 19.2;
  - D16-BF4096 (decoupled 16k-token parts, T = 0, forced), 20.2;
  - D16-T1-BF8192, 18.1;
  - D32-T1, 18.6.
- **Dropped:**
  - A0 (production), and D4/D8/D16/D32 at T = 0: loop to the cap;
  - D4-T1 and D16-T1: grammar escape;
  - D8-T1: empty answer.
- A 4/4 arm's Wilson interval is [0.51, 1.00]. Stage 1 prunes; it certifies nothing.
- Stage 2 goes on with k = 16 and k = 32, both forced (LOG 08:04, 10-02).

---

## 3. Where it stands right now

### 3.1 The running process

- **What is running:** `harness/stage2.py round1 …`, started 2026-10-03 14:57 EDT by
  `harness/round1.sh`, from
  `~/git/vibey-storm/research-large-diff-review/research/large-diff-review/experiments`.
  It resumes from the cache and skips every finished (arm, case, part).
- **Etiquette:** it yields routinely to CI reviews, as designed. `results/stage2.log`
  shows `[etiquette] yielded … re-queued`.
- **Store:** 361 requests and 16.94 model-hours (`analyze.py requests`, 18:05 EDT).
- **Adjudications:** one hand adjudication (`results/adjudication.jsonl`: D16-T1-BF8192's
  "UltraVerdict not imported" on #1161 part 1 is FALSE).
- **Voids:**
  - 2 contention voids (D4-T1 #1131 parts 4–5, 10-01 23:20);
  - 1 server-outage void (needle-1155-sql-ledger-range-order-middle, rows 128 and 129,
    plus request 9889ca0b…, 10-03 14:58).

### 3.2 Stage 2 round 1: 8 of 17 arms scored, 9th in progress

Round 1 is fixed by LOG 08:04 (10-02): 9 dev needle parts (#1131, #1155 and #1161, at
early/middle/late) plus 3 seeded clean parts per host. The arms run in this order:

D16-T1-BF8192 (base), D32-T1-BF8192, D16-BF4096, A2, A1, +FF, +VER, +SA, +CTXnone,
+CTXfile, +TRI, D16-T1-high-BF8192, D16-T1-BF4096, D16-T1-BF12288, D16-T1-low-BF8192
(negative control only), D16-TD@qwen3:14b, D16-TD@qwen2.5-coder:14b.

`analyze.py s2` at 18:05 EDT. This is **interim**: n = 9 per arm, and nothing may be
decided on it.

| arm | needle parts caught | recall (Wilson 95%) | clean parts blocked | FP/part | mean min/req |
|---|---|---|---|---|---|
| A1 | 5/9 | 0.56 [0.27, 0.81] | 4/9 | 0.44 | 5.3 |
| A2 | 7/9 | 0.78 [0.45, 0.94] | 5/9 | 0.56 | 5.2 |
| D16-BF4096 | 6/9 | 0.67 [0.35, 0.88] | 2/9 | 0.22 | 3.3 |
| D16-T1-BF8192 | 7/9 | 0.78 [0.45, 0.94] | 1/9 | 0.11 | 3.0 |
| D16-T1-BF8192+FF | 6/9 | 0.67 [0.35, 0.88] | 1/9 | 0.11 | 3.4 |
| D16-T1-BF8192+SA | 6/9 | 0.67 [0.35, 0.88] | 1/9 | 0.11 | 3.1 |
| D16-T1-BF8192+VER | 7/9 | 0.78 [0.45, 0.94] | 0/9 | 0.00 [0.00, 0.30] | 3.7 |
| D32-T1-BF8192 | 6/9 | 0.67 [0.35, 0.88] | 5/8 | 0.62 | 5.2 |
| D16-T1-BF8192+CTXnone | 4/6 | (partial) | 0/0 | n/a | 1.2 |

**Why the FP column matters most (Hm4).** A diff cut into m parts has a diff-level
FP of 1 − Π(1 − fp_part).

- At m ≈ 6 (16k-token parts plus the contract request on the S2 hosts; #1131 is 5 parts
  at 16k), a per-part FP of 0.11 composes to about 0.50 per diff.
- Only a verifier-like step can bring the per-part rate down to where the diff-level
  rate is tolerable.
- +VER's 0/9 still has an upper bound of 0.30 per part. Round 2 exists to narrow that.

Do not pre-judge the winner. The halving score decides it.

### 3.3 Branches and PRs

- The research snapshots land on `develop` through `research/large-diff-review-N`
  draft PRs. The latest merged is #1387; the worktree is at `5917e53dd`.
- **`develop` was realigned on 2026-10-03:**
  - #1390 promoted `develop` to `main` by hand, without the release commit;
  - 4.0.0 was then cut as #1396.
  - Merge `origin/develop` into the research branch before the next snapshot.
  - Expect new SHAs everywhere.

### 3.4 Deviations already owed to LOG.md

Write these before you read any data they affect:

1. **Canary corpus re-pin.** The preregistration pins the canary corpus at `2b17eb7`.
   On 2026-10-03 the pin became `0f88412d508364fbc42c6c9a413235899e7859cd`, the
   identical tree (`b93c7e8f`), because the realignment orphaned `2b17eb7`. The cases are
   byte-identical, and A0's canary verdicts in `results/b0-canary/` stay valid. Log it
   as a deviation with no content change.
2. **Not run, for time** (already declared in LOG 08:04): SM (small-model triage) and
   gemma4:26b. They stay declared gaps; they are not silently dropped.

---

## 4. The gap, in order: every step from here to done

### Phase A: finish Stage 2 round 1

- **Let the chain finish.** These arms remain:
  - the rest of +CTXnone;
  - +CTXfile;
  - +TRI;
  - D16-T1-high-BF8192;
  - D16-T1-BF4096 and D16-T1-BF12288 (the R sweep);
  - D16-T1-low-BF8192, run **once**, labelled as the negative control and kept out of
    the halving (LOG 18:40, 10-01);
  - the two alternative reviewers (`@qwen3:14b`, `@qwen2.5-coder:14b`). Swap models only
    when no other client is active, and batch the requests by model.

  At about 3–5 min per request plus CI contention, expect roughly 12–20 more hours.
  That figure is an estimate, not a promise.
- **Run the contention audit** (`contention.py audit --write`) at the round boundary,
  and void what it flags before you compute anything.
- **Adjudicate by hand** every blocking finding on a clean part, appending to
  `adjudication.jsonl` with evidence at the merge commit. Report FP both raw and
  adjudicated.
- **Score +CONS on every arm** at no model cost (`harness/cons.py`).
- **Compute the halving score** as fixed: part recall − composed diff-level FP (m = the
  arm's mean parts per S2 host), ties broken by mean minutes per request. Write the
  ranking into LOG.md.

### Phase B: Stage 2 round 2

- The better half by score runs on **all** the development cases: the 9 dev needles × 2
  positions on the S2 hosts (#1131, #1155, #1161, #1250, #1282, #1305), plus their
  clean parts.
- Before Stage 3, name in LOG.md **the winner and at most three combinations** of
  round-2 survivors (for example base+VER+FF, if both survive). Run the combinations on
  the same cases. Pick the final method by the same score.
- Freeze it. From here on, nothing changes the method (PREREGISTRATION §6.3).

### Phase C: measurements the registration owes and that are not yet done

1. **The Hm2 replay** (deferred in LOG 19:55, 10-01). Replay #1312's part 1 and #1317's
   part 3 at T = 0 and at T = 1 × 5 seeds. Log eval_count, done_reason, wall time, the
   repeated-8-gram fraction and PRIOR-ART's loop metric. #1317 is a holdout host: read
   only completion and loop metrics from it, never verdict content.
2. **Hm3 forced-verdict fidelity.** Re-run requests that finished naturally with R below
   their natural length, and compare the verdicts (agreement, CAUGHT kept).
3. **Replication.** Re-run ≥ 10% of Stage 2–3 requests, chosen by seed, with the cache
   bypassed, and report agreement of verdict and of CAUGHT. Part-level composition is
   valid only if this holds (§5).
4. **Secondary matcher sensitivity:** file ± 5 lines plus the class keyword, reported
   beside the canary's ± 3.
5. **Reporting dimensions.** Report every result stratified by content type (code, tests
   and docs share), and verdict consistency (INCONSISTENT as defined at LOG 19:45) for
   every arm.

### Phase D: Stage 3 confirmation (holdout; untouched until now)

- **Winner and A0** on the 12 confirmation hosts (#1121, #1137, #1166, #1170, #1249,
  #1251, #1252, #1259, #1307, #1313, #1317, #1323) as clean controls, each with three
  holdout needles at early/middle/late: 36 defect cases, 48 diffs in all.
- **The whole canary corpus** (27 defects + 14 controls), paired with A0's existing
  verdicts in `results/b0-canary/` (from #1331, sha256 in `SHA256SUMS`).
- The preregistration estimates about 15 h of model time; expect more under CI load.
- Apply §7's rules exactly, each reported PASS / FAIL / INCONCLUSIVE:
  1. verdict rate ≥ 0.95 on the 48 (with its Wilson lower bound, ≥ 0.80, or the claim
     is "inconclusive"), every diff within T_cap; also report the host-clustered bound;
  2. recall on the 27 small defects non-inferior to A0: the paired lower bound
     of recall(M) − recall(A0) > −0.15;
  3. FP not raised: the upper bound of FP(M) − FP(A0) on the 14 controls < +0.15; FP(M)
     on the 12 large controls reported with its interval.

  Also report large-diff recall against A0's effective recall on the same 36 cases.
- **INCONCLUSIVE is a likely and honest outcome** (§8: 27 defects give a half-width of
  about 0.12–0.20). Do not rescue it with post-hoc cuts.

### Phase E: write it up

- Fill in REPORT.md: Stage 2, Stage 3, Discussion (threats per §9, held up against what
  happened), and **Implementation plan**. Every figure comes from `analyze.py`, and every
  deviation is listed in Methods.
- Update the paper section on recall (`docs/paper.md`, around "Recall, measured
  offline") with the confirmed result and its intervals, citing the data snapshot by
  commit. Pin that commit only to an ancestor of `origin/develop`.

### Phase F: implement the selected method in production

Do this only if Stage 3 passes. If criterion 1 passes but 2 or 3 is INCONCLUSIVE, ship
behind a declared flag that defaults off, and say why. If it fails, ship nothing, write
up the negative result, and propose the next study.

The production path, from a code map made at the cutoff (verify each line number before
you edit; `vg/` = `src/vibey_tools/gh/vibey_gh/`):

| Change, if the winner needs it | Where it lands now |
|---|---|
| Sampling (temperature / top_p / seed) declared, not hard-coded 0 | `vg/local_review.py:1110` (`review_payload`), `:776` (slot probe), `:2234` (triage) |
| Budget forcing: phase-2 prefill with `format` kept, after a `length` / unusable / empty answer | `SizedChat` (`:835-1038`); `answer()` at `:969-1038` raises the refusal codes to repair on (`review_outcome.py:117-131`) |
| Separate thinking and answer budgets | `num_predict = sizer.reserve` at `:902`; reserve 16,384 |
| A constant `num_ctx` per host (no runner reloads) | `:895` → `fit.ContextSizer.num_ctx` (`fit.py:730-732`) |
| A check-code placement that keeps a shared, cacheable prefix | `CANARY_HEAD`/`CANARY_TAIL` `:233-239`, `seal` `:835`/`:854-855` |
| Decoupled parts: defect requests without documents + one contract request on a diff digest; strict reduce | `DiffChunker` `:1403-1505` (with the lenient oversize-hunk rule the harness uses), `plan()` `:1691-1718`, `room()` `:1618-1632`, `compose()` `:1809-1848`, `WholeReview` `:504`/`:603` |
| Findings-first schema (+FF) | `REVIEW_SCHEMA` `:77-97`; `review_contract.py:123-140` (whose comment says the order is deliberate, so amend it with the evidence) |
| Verifier (+VER): N = 3 at T = 1, keep at ≥ 2/3 TRUE, UNCERTAIN kept | new class + interface beside `local_review.py`; port the harness's `review.Verifier` |
| Triage (+TRI) / static hints (+SA) | new classes; port `review.Triage` / `review.StaticAnalysis` |
| Config keys for all of the above, with defaults from the winner | `PrAutomationFallbackConfig`, `vg/config.py:504` (fields `:524-637`, validation `:659-760`), parsed at `:3301`/`:3337`; document in `src/vibey_tools/gh/docs/configuration.md` |
| CLI flags | `review()` `:1895`; then **the managed template** `vg/templates/workflows/pr-review.yml` (`:652-672`), **both** renders (`.github/workflows/pr-review.yml` and `src/vibey_tools/gh/.github/workflows/pr-review.yml`), and `ReviewCanary.argv`/`settings` (`vg/review_canary.py:736-815`). `test_review_canary.py:758-804` and `test_templates.py:534-663` hold all of them in sync, and `tools-lint` checks the two renders for drift |
| A declared job timeout matching T_cap (none today, so GitHub's 360 min applies) | `review-sovereign` job, `pr-review.yml:381` |

Requirements for that change:

- **Structure:** classes with interfaces in `vg/interfaces/` (`local_review_interface.py`
  has `SovereignReviewInterface` at `:351`).
- **Tests:** vibey-gh's own suite on 3.12, 3.13 and 3.14 (CI `tools` job), and black +
  isort + mypy (CI `tools-lint`).
- **Records:**
  - changelog fragments in `src/vibey_tools/gh/changelog.d/` and `changelog.d/`;
  - a new ADR (the next free number; currently 0083) recording the decision and the
    evidence, added to the `properdocs.yml` nav, with `python scripts/llms_txt.py` re-run
    and the ADR count updated in CLAUDE.md, AGENTS.md, GEMINI.md, README.md and
    `docs/index.md` (`tests/meta/test_adr_counts.py`).
  - If the change embodies a governing rule (for example "never review at temperature 0"),
    draft it as a sub-doctrine for the operator's ratifying merge. Never ratify it
    yourself.
- **Agent surfaces:** if a skill or procedure changes, update all four trees
  (`.claude/skills/`, `.agents/skills/`, `.cursor/rules/`, `.agent/rules/`) in the same
  PR.

### Phase G: the calibration deliverable (operator amendment, 2026-10-01 22:09Z, LOG 18:45)

This is part of done, not a follow-up.

1. **A shipped, deterministic full calibration:**
   - **Structure:** a class + interface, a TOML config, a pinned corpus manifest (pins
     must be ancestors of `origin/develop`), seeds, and needles.
   - **What it runs:** the winner vs A0, plus a sweep that picks *this host's* operating
     point (part size, think, temperature/top_p, thinking and answer budgets, verifier N).
   - **What it writes:** an **append-only calibration record** with a host fingerprint
     (CPU, cores, memory, OS, Ollama version, model digests; reuse
     `vg/slots.py` `DeviceFingerprint` `:137` and ADR-0058) and a **per-host operating
     profile** that the review reads at run time.
   - **Schedule:** monthly on `vibey-local-vibey`, by a workflow modelled on
     `minimum-specs.yml` (weekly cron `23 7 * * 1`, 150 min). It lands its record via PR.
     `review-canary.yml` (weekly, 600 min, opens a PR) is the closer precedent for the
     record-and-PR pattern.
2. **A `vibey doctor` "review calibration" section** (runs in minutes):
   - it shows the latest record, its age, and a same-host check;
   - it FAILs when the record is missing, older than a declared limit, from another host,
     or for another model digest;
   - it runs a smoke probe (one known needle + one control);
   - an opt-in `--calibrate-review` triggers the full run.

   It slots in after `HOST_HEALTH.doctor_lines()` at `src/vibey/cli/main.py:1625`. Follow
   the `(lines, ok)` singleton pattern of `src/vibey/cli/host_health.py:67,90` with its
   interface in `cli/interfaces/`, and add its `ok` to the exit-code aggregation at
   `:1628-1637`. Check the import-linter contracts before `src/vibey` imports anything
   from `vibey_gh`. vibey-gh's own `vg/doctor.py` (`diagnose` `:295`) may be the better
   home for the probe, with `vibey doctor` calling it.

### Phase H: verify in production and close the loop

- **Re-measure with the canary lane** (`review-canary.yml`, or
  `vibey-gh review-canary run` on the host) using the new settings. Append the result to
  the canary ledger and show it in the runbook block
  (`docs/runbooks/sovereign-review-runner.md`, `render --check`).
- **Watch real large PRs** through `review-sovereign` until at least N large PRs (declare
  N before you look) reach a verdict. Record the outcomes as evidence under
  `docs/architecture/evidence/`. A large PR that still reaches "a human is needed" is
  reported, not explained away.
- **Update the issues with evidence** (object, source, cutoff), notably #133 ("the
  sovereign lane is primary for the diff half of review … close with live evidence").
  Close only what the live evidence actually closes.

---

## 5. Definition of done

All of the following, each with its evidence named:

- [ ] Stage 2 rounds 1 and 2 complete; contention audits run; voids recorded in both
      files; the winner and ≤ 3 combinations named in LOG.md before Stage 3.
- [ ] Hm2 replay, Hm3 fidelity, ≥ 10% replication, matcher sensitivity, content-type
      strata and verdict consistency all reported.
- [ ] Stage 3 run on the holdout, untouched until then; §7's three criteria each reported
      PASS / FAIL / INCONCLUSIVE with intervals; large-diff recall against A0's effective
      recall.
- [ ] REPORT.md complete (Methods with every deviation, Results, Discussion,
      Implementation plan); paper updated; data snapshot committed and pushed.
- [ ] If the method passed: it is in `vibey-gh local-review`, configured from
      `[pr_automation.fallback]` with defaults from the evidence, wired through the
      template, both renders and the canary argv, with a declared job timeout; tests
      green on 3.12–3.14; ADR written; changelog fragments added. If it did not pass, the
      negative result is written up and nothing ships enabled.
- [ ] The calibration ships: the monthly workflow, the append-only record with host
      fingerprint, the per-host operating profile read by the review, and the
      `vibey doctor` section with smoke probe and `--calibrate-review`.
- [ ] Production verification: the canary re-measured on the new method; real large PRs
      reaching verdicts, recorded; issues updated with evidence-bounded status.
- [ ] Everything landed as PRs through the merge train; nothing pushed to a protected
      branch; no gate bypassed.

---

## 6. Traps this project has already hit

- **The Docker runner is invisible to `ps`.** Only the TCP-connection check sees it
  (LOG 23:20, 10-01).
- **Transport errors are cached as results.** Voiding one takes the request store *and*
  the diff ledger (LOG 14:59, 10-03).
- **Harness messages in stdout corrupt** the captured verdict JSON. They go to
  `sys.__stdout__` (LOG 05:16, 10-02).
- **Never run two harness processes.** The flock exists because one queued behind the
  other inside Ollama (LOG 19:47, 10-01).
- **A small part can run to the cap too.** Content matters, not only size (EVIDENCE;
  LOG 19:47).
- **A hand promotion skips the release step.** #1390 put 4.0.0's content on `main` at
  version 3.4.0, and its green Release run published nothing (PyPI `skip-existing`).
  Promote with `vibey-gh promote`.
- **`vibey-gh version --since origin/main` reads the local HEAD.** Derive at
  `origin/develop`.
- **Never quote a skip-CI marker in any commit body.** GitHub skips every workflow for
  that commit.
- **The pre-push hooks test the working tree.** Never edit a file while a hook runs.
  Commit and push in the foreground.

## 7. How to report

At each stage boundary, send the operator a short status:

- what finished, with the counts from `analyze.py` and the time read;
- what was voided and why;
- what was decided and where in LOG.md it was written before the data;
- what is next, with an estimate labelled as an estimate.

Refusals and inconclusive results are reportable outcomes, not failures to hide.
