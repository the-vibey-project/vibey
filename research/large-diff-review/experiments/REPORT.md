# A sovereign review that reaches a verdict on large diffs — method and evidence

**Status: in progress (Stage 2 running).** Every number below names its source in `data/`
(the committed snapshot of the live `results/`) and is reproducible with
`harness/analyze.py`. Nothing here is stated that the store does not hold. Registration:
`PREREGISTRATION.md` (committed before the first request); every deviation: `LOG.md`.

## Introduction

vibey's sovereign pull-request review runs `gpt-oss:20b` on Ollama on one Apple M5 host
(24 GB, one model slot), shared with live CI reviews. Small diffs get verdicts; large ones
did not: #1317's third part wrote 78,418 reasoning characters and no answer
(`done_reason=length`, 39.5 min) and #1312 timed out mid-reasoning. The question
(PICO, PREREGISTRATION §1): for diffs too large for one production request, which review
method reaches a verdict on ≥ 95% of them in bounded time, without losing recall on
planted defects or raising false positives, against the production method (B0 = A0)?

Two sibling tracks fed in before any data: PRIOR-ART (`../prior-art/findings.md`: greedy
decoding loops gpt-oss's reasoning; Ollama's assistant prefill can force a final answer;
small units help) and EVIDENCE (`../evidence/findings.md`: from 145 past review requests,
P(finish within 16,384 tokens) falls from 0.92 at 20k prompt tokens to 0.36 at 50k).

## Methods

**Corpus.** 45 "large" diffs — every PR merged into develop 2026-09-25..10-01 whose diff
exceeds one production request (`SovereignReview.room`), rebuilt from its squash merge
commit with its documents and changed files' text; dev 22 / holdout 23 by seed
20261001. Needles: the review canary's 27 planted defects (9 classes), each spliced into a
host as an extra file at 5% / 50% / 95% of the diff; dev 9 / holdout 18 by seed. Controls:
the merged hosts and the canary's 14 controls. Matching: the canary's `FindingMatcher`
unchanged (my scorer reproduces the canary lane's 18/25 recall and 0/14 FP exactly).

**Harness** (`harness/`). One door to the model (`client.Model`): it waits until no
review process runs, no other TCP client holds Ollama's port (the CI runner is in Docker,
invisible to `ps`), and the server log shows nothing in flight; it aborts only its own
request if a live review appears; and it appends each request's telemetry (model, options,
prompt/eval tokens, reasoning/answer chars, done_reason, wall time, slot wait, host
fingerprint) to `results/requests.jsonl`, keyed by the SHA-256 of the exact body, so a run
resumes and identical requests are asked once. A contention audit (`contention.py`)
matches every record to the server's access log and voids any that queued behind
another client. Production arms go through `local_review.review(argv)` itself, with only
the transport patched; the D arms reuse production's chunker, source excerpts, prompts,
check-code seal and answer validation. Production settings are pinned against the
registration at run time.

**Arms** (PREREGISTRATION §3; LOG.md amendments). A0 = production. A1 = A0 + budget
forcing at 4,096 reasoning tokens. A2 = A0 at temperature 1.0 / top_p 1.0 / seed 42 (the
model's own default sampling). D_k = the diff cut by production's chunker into parts of
≤ k diff tokens, each a defect request with its own reference excerpts and no documents,
plus one documentation-contract request (documents + a diff digest); strict reduce (any
request without a verdict ⇒ no verdict). Suffixes: -T1 (T=1 sampling), -BF_R (forcing at
R), -low/-high (think), +FF (findings before pass in the schema), +VER (3-vote verifier),
+SA (ruff/bandit hints), +CTXnone/+CTXfile (reference context), +TRI (deterministic
triage), @model (alternative reviewer).

**Forcing** (Stage 0, LOG.md 19:13): phase 1 is the arm's own request with
`num_predict = R`; if it ends without a usable answer, phase 2 repeats the messages plus an
assistant message carrying the phase-1 reasoning, a one-line budget note and content " ",
with the `format` grammar kept. Verified: the harmony rendering is exact (687 = 687 prompt
tokens chat vs raw), the grammar still constrains a prefilled final channel, and the
prompt+reasoning KV is reused (phase 2 costs ~4 s on 20–40k-token parts).

**Statistics.** Wilson 95% intervals; Newcombe hybrid-score / method-10 intervals for
differences (`harness/stats.py`).

## Results

### Mechanism: why production gives no verdict on large diffs
- On the identical request (#1131 D8 part 1, 13,894 prompt tokens) T=0 ran to the
  16,384-token cap in 697 s with no answer; 86% of its word 8-grams repeat and its tail is
  one sentence verbatim, ×N, including "This is obviously not helpful. Let's step back."
  followed by the same loop. At T=1.0/top_p 1.0/seed 42 it answered in 368 tokens, 39 s.
  (`data/requests.jsonl`, `arm=D8` and `arm=D8-T1`, `#1131 part1`.)
- Production (A0) on #1131: part 1 (38,466 prompt tokens) ran to the cap, 953 s, no
  verdict. Production with ONLY temperature changed (A2) reached a verdict on all four
  Stage 1 hosts.
- At T=1 two rarer failures remain: the answer escapes the `format` grammar (seen twice:
  bare check codes then JSON with keys outside the schema), and the turn ends in the
  analysis channel with an empty answer (once). Forcing repaired every such case it met.
- Production sizes `num_ctx` per request, so the runner reloads on most requests
  (EVIDENCE: 72% of CI requests); and its check code opens the system prompt, so no two
  requests share a cacheable prefix.

### Deterministic baseline (no model)
SA-only (ruff `--select ALL` + bandit, diagnostics the change introduces on the lines it
touches): 5/27 canary defects (3/3 SQL injection, 2/3 swallowed exception), 0/14 controls.

### Stage 1 — screening (verdict and time; 4 dev hosts, 161–225k chars)
| arm | verdicts | wall p50 / max (min) | outcome |
|---|---|---|---|
| A0 production | 0/1 | 15.9 | dropped (loop to cap) |
| A1 production + forcing 4,096 | 4/4 | 18.4 / 22.7 | kept |
| A2 production at T=1 | 4/4 | 19.2 / 26.9 | kept |
| D16-BF4096 (T=0, forced) | 4/4 | 20.2 / 24.0 | kept |
| D16-T1-BF8192 | 4/4 | 18.1 / 25.3 | kept |
| D32-T1 | 4/4 | 18.6 / 19.8 | kept |
| D16-T1 | 3/4 | 16.6 / 19.2 | dropped (grammar escape) |
| D8-T1 | 3/4 | 23.0 / 28.0 | dropped (empty answer) |
| D4-T1 | 0/1 | 12.5 | dropped (grammar escape) |
| D4, D8, D16, D32 at T=0 | 0/1 each | 11.6–29.2 | dropped (loop to cap) |

A 4/4 arm's Wilson interval is [0.51, 1.00]: Stage 1 prunes; it does not certify.

### Stage 2 — successive halving (recall, false positives) — _pending_
### Stage 3 — confirmation on holdout — _pending_

## Discussion — _pending_

## Implementation plan for vibey-gh — _pending (after Stage 3)_
