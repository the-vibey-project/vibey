# Prior art: verdicts on large diffs with a local gpt-oss:20b — findings

Evidence cutoff: 2026-10-01. Bracketed ids refer to sources.md. "Verified in source" means the
code was read; not yet confirmed by a live call (this track ran no local model).

Note (main session, 2026-10-01): confirmed in vibey's own code that the review requests run at
temperature 0 — `src/vibey_tools/gh/vibey_gh/local_review.py:1110` and `:2234` send
`"options": {"temperature": 0}` — so suspect (a) in §0.2 applies to this repository as built.

## 0. Bottom line
1. No off-the-shelf solution fits. Nothing found targets one local 20B reasoning model at
   ~22 tok/s with no paid fallback. PR-Agent [D1] handles large diffs by not reviewing what
   does not fit (overflow files listed by name) or <=3 chunk calls, with no thinking-budget
   control for Ollama. Commercial tools (CodeRabbit, Copilot, Greptile, Graphite, Bito,
   Ellipsis) are closed, use frontier models, publish limits but not recall. Patterns
   transfer; products do not.
2. Two cheap suspects for the runaway: (a) temperature 0 [D-ctx] vs OpenAI's recommended
   temperature 1.0/top_p 1.0 [A3] and Ollama's shipped temperature 1 [A4]; greedy decoding
   looped gpt-oss-20b's CoT on 81% of tested prompts [A10]. (b) Nothing bounds thinking
   separately from the answer: no Ollama thinking budget [A4, A6]; reasoning and answer share
   num_predict [A9] — the #1317 symptom.
3. A verdict can be forced via Ollama's supported assistant prefill [A4] (s1 budget forcing
   [B1]). It guarantees a verdict, not a good one; forcing early costs accuracy [B1-B3].
4. Recall/FP evidence favours smaller review units: recall falls with issues per PR and diff
   size [E1, E3]; whole-window review 16-22% vs per-unit 50-60% [E5]; adding file context
   lowered detection in 8/8 models [C3]; long input alone degrades and even shortens
   reasoning (gpt-oss-120b) [C1, B4].
5. Cut FPs with a separate verify step on small inputs: gpt-oss-20b adjudicates single claims
   at ~96-100% recall/specificity with a consistency check [E4]; two-stage filters raised
   precision 57->66-75% [D10]. Caveat: Atlassian's LLM factual judge had minimal effect;
   their gain came from a trained actionability filter [D11].

## 1. Off-the-shelf? (summary table)
PR-Agent: size-sorted packing to max_model_tokens 32k minus 1,500 buffer; deletion-only hunks
dropped; overflow listed not reviewed; large_patch_policy clip/skip; opt-in chunking (3 calls);
/improve self-reflection scoring. Beko: 73.8% comments resolved, closure 5h52m->8h20m [D2].
CodeRabbit: per-file; light-model summary+trivial triage; heavy-model review (~50% cost saving,
vendor) [D3]; 150-300 files/review [D4]. Copilot: agentic, plans long PRs, records findings as
it reads; 300-file/20k-line limit lifted Aug 2026; silent on 29% of reviews (vendor) [D5].
Meta RADAR: risk funnel, codemods bypass AI review, revert 1/3 and incidents 1/50 (observational)
[D9]. AutoCommenter: per-file 2,048 tokens, per-category thresholds, drop unchanged-line comments,
~40% resolution [D7]. BitsAI-CR: detector->filter, precision 57->66% offline, 75% online [D10].
RovoDev: 38.7% resolution vs 44.5% human [D11]. Ericsson: local 7-13B + enclosing method [D12].
llama.cpp --reasoning-budget exists [A7] but Ollama passes no budget [A4]. Answer: no.

## 2. Ranked techniques (time model t ~= prompt/275 + generated/22 s; 16,384 gen ~= 12.4 min)
T1 Sample to spec (T=1.0, top_p=1.0, explicit seed). Evidence moderate (model-specific).
   Test: replay #1317 p3 and #1312 p1 at T0 vs T1 x 5 seeds; log eval_count, done_reason, loop
   metric on thinking. Free.
T2 Bounded thinking + forced final via /api/chat prefill (phase 2 assistant message with
   thinking + budget note + non-empty content prefix; same think level; num_predict A).
   Evidence: strong mechanism [B1], budget message helps (89 vs 79%) [A7], GPT-OSS-20B anytime
   but leaks reasoning when interrupted early [B2], forced extraction reliable only late
   (>=70% of trace: <5 pp) [B3]. Label forced verdicts. Sweep B 4k/8k/12k; check phase-2
   prompt_eval_count; measure forced-vs-natural agreement.
T3 Small units (diff <=8-12k tokens/part) + 200-400-token PR digest, structured per-part
   results, deterministic reduce (verified blocking finding->FAIL; all parts pass->PASS; any
   unreviewed part->explicit NO-VERDICT). Evidence moderate-strong, convergent [E1, E3, E5, C3,
   C1, B4, D5]. Example: 40k diff as 6x(4k+1k) = 30k gen ~23 min worst vs 3x16k = 48k ~36 min.
   Risk: cross-part defects; digest mitigates; measure.
T4 Deterministic triage: -M100% renames, empty `git diff -w`, deletion-only hunks listed,
   generated/vendored/lockfiles by path, identical substitution sets (review one + mechanical
   check). Report every skip. Evidence strong deployment [D1, D3, D5, D9], weak recall data.
T5 Verify blocking findings: claim + cited code (+ enclosing fn), conclusion-first
   TRUE/FALSE/UNCERTAIN, think low/medium, N=3, keep >=2/3 TRUE, UNCERTAIN -> human gate.
   Evidence strong for gpt-oss-20b adjudication [E4], [D10], [D1]; counter [D11], [E9].
T6 Multi-sample only for forced/looped/borderline parts (recall +118%, F1 +44% at n=10 [E1];
   parallel > extended thinking [B9]; cross-model unions hurt F1 [E3]).
T7 Effort per part: medium default, high for flagged parts, never low for verdicts
   (SWE-bench 37.4/53.2/60.7 [A1]); never tell it to hurry (panic) [B2].
Not now: BAEE/DEER early exit (costly on one slot), fine-tuning remedies, bypassing Ollama for
llama.cpp budget (harmony support unverified).

## 3. Parameters and exact Ollama mechanics
temperature/top_p 0/default -> 1.0/1.0 + seed; think ""(medium) -> medium, high for flagged;
part prompt up to ~57k -> diff 8-12k + digest, enclosing-function context (test vs whole file);
thinking budget none -> sweep 4k/8k/12k counted on stream; answer A 1.5-2.5k; loop guard: abort
if >=200-char substring repeats >=3x in last ~4k chars; force note in thinking tail; content
prefix = first line of required output; retry with new seed at T1, else accept labelled forced;
verify blocking findings N=3 >=2/3.
Ollama (main / 0.35.0): think low|medium|high ("max"->high, bools ignored; sets "Reasoning:");
num_predict caps thinking+content, done_reason "length"; prefill: assistant{thinking, content
non-empty} continues final channel, {thinking only} continues analysis; thinking rendered only
after last user message; raw:true = no template, no harmony parser, raw `response`, no context;
EOS 200002/199999/200012, <|end|> 200007 not EOS; llama-server cache_prompt true (verify reuse via
prompt_eval_count; n_slots=1 evicts); no thinking-budget field anywhere in Ollama's path.

## 4. Expected effects
T1: verdict up, latency down, recall/FP unknown. T2: verdict ~100%, hard time bound, recall
down and FP risk for forced parts. T3: verdict up, recall up, FP down. T4: verdict up, latency
down, recall neutral if exact rules. T5: FP down, slight recall cost, bounded extra time.
T6: up on retried parts at n x cost. T7: tunable. Test order: T1 -> T2 -> T4 -> T3 -> T5 -> T6/T7.

## 5. Evaluation methodology
Seed defects into real large vibey diffs at controlled positions (start/middle/end) and
interleaved with benign churn [E5, C2]; never synthetic-only (~10x overstatement [E3]).
Real-defect oracle: later fix commits touching the same lines [D10, D11]; c-CRAB-style
fail-then-pass tests where feasible [E2]. Matching: deterministic file + +-5 lines + type, LLM
judge for ambiguous [E3]; report P/R/F1 and FPs per PR [E1]; PLAUSIBLE class [C3]. Verdict
reliability: >=3 seeds, kappa on verdicts, natural vs forced share, coverage share (reviewed /
triaged / unreviewed). Forced-verdict fidelity: impose budgets on runs that finish naturally and
compare. Ops: verdict rate on large diffs (target >=95%), p50/p95 wall time, tokens, loop rate.

## 6. Open questions
(1) Does T=1.0 remove the runaways; effect on precision? (2) Quality loss of forced answers for
open-ended review at 4k/8k/12k? (3) KV prefix reuse for phase-2 prefill? (4) Raw-mode
special-token tokenization on Ollama's llama-server path? (5) Does full-file context help or
hurt vibey specifically? (6) Cross-part recall loss and digest recovery? (7) Which verifier
regime applies — CMU's strong result or Atlassian's null result, with correlated same-model
errors? (8) Gaps: no gpt-oss-20b study of reasoning length vs input length on code; vendor
claims unverified; RULER/LongCodeBench/Mozilla/JetBrains/Sweep/reviewdog not covered in depth.
