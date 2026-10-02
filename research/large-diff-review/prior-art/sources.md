# Annotated bibliography (Chicago author-date)

Accessed 2026-10-01 unless noted. Each entry: citation; what it actually claims (paraphrased,
short quotes only where the wording matters); credibility note (CRAAP/SIFT: currency,
relevance, authority, accuracy, purpose; "vendor" = the claim is the seller's own and was not
independently verified). Grouped by theme. Numbers in [brackets] are used as cross-refs in
findings.md.

Note: for INC-A entries B5-B10 and D8 the first-author names were taken from memory and the
abstract listing, not from the paper PDF; verify before formal citation (cite by arXiv id /
URL meanwhile).

## A. Runtime facts: Ollama, harmony, gpt-oss

[A1] OpenAI. 2025. "gpt-oss-120b & gpt-oss-20b Model Card." arXiv:2508.10925.
https://arxiv.org/abs/2508.10925.
Claims: three trained reasoning levels set by "Reasoning: low/medium/high" in the system
prompt; higher level = longer CoT, log-linear accuracy returns; gpt-oss-20b "use[s] over 20k
CoT tokens per problem on average for AIME"; SWE-bench Verified for 20b 37.4 / 53.2 / 60.7
at low / medium / high (Table 3); multi-turn CoT from past turns should be removed; context
131,072 via YaRN. Credibility: primary, authoritative for the model; self-reported evals on
OpenAI's harness; benchmarks are math/coding, not code review.

[A2] OpenAI. 2025. "OpenAI Harmony Response Format." OpenAI Cookbook / developers.openai.com.
https://developers.openai.com/cookbook/articles/openai-harmony; and OpenAI. 2025. "harmony
docs/format.md." GitHub. https://github.com/openai/harmony.
Claims: tokens `<|start|>`(200006) `<|channel|>`(200005) `<|message|>`(200008)
`<|end|>`(200007) `<|return|>`(200002, stop) `<|call|>`(200012, stop); channels analysis /
commentary / final; prompt ends with `<|start|>assistant` and the model writes the channel.
Credibility: primary spec.

[A3] OpenAI. 2025. "gpt-oss README" (Recommended Sampling Parameters). GitHub.
https://github.com/openai/gpt-oss. And Hugging Face model repo openai/gpt-oss-20b
(README.md, generation_config.json). https://huggingface.co/openai/gpt-oss-20b.
Claims: "We recommend sampling with `temperature=1.0` and `top_p=1.0`"; generation_config has
`do_sample: true`, EOS ids 200002, 199999, 200012 (so `<|end|>` is not an EOS token).
Credibility: primary.

[A4] Ollama. 2026. Source code, branch main (server/routes.go, llm/llama_server.go,
llm/server.go, server/prompt.go, harmony/harmonyparser.go) and model page template/params
for gpt-oss:20b. GitHub / ollama.com. https://github.com/ollama/ollama ;
https://ollama.com/library/gpt-oss:20b. Read 2026-10-01; harmonyparser.go last changed
2026-09-22 (commit a9d8953ab0); latest tag v0.35.1-rc0 (2026-09-29); local server 0.35.0.
What the code shows (my reading): gpt-oss uses the "harmony" parser; `think:"max"` is mapped
to "high"; with `raw:true` on /api/generate no template and no parser is applied; GGML models
run on llama-server exclusively since 2026-05-29 with `cache_prompt: true`; the llama-server
request Ollama builds has no reasoning-budget field; the gpt-oss chat template supports
assistant prefill (content -> continues the final channel; thinking only -> continues the
analysis channel) and the harmony handler has an explicit `contentPrefill` mode; the strings
that close thinking are `<|end|><|start|>assistant<|channel|>final<|message|>` (and json /
commentary variants); the model's shipped params are `{"temperature": 1}`.
Credibility: primary (code is the behaviour); version-specific; my reading not yet verified
by a live call (the experiment track must confirm).

[A5] Ollama. 2026. "Thinking." docs.ollama.com. https://docs.ollama.com/capabilities/thinking.
Claims: gpt-oss expects `think` in {low, medium, high}; booleans ignored; `/api/show` returns
`thinking.values` and `default: "medium"`; the trace "cannot be fully disabled" for gpt-oss.
Credibility: primary docs.

[A6] mann1x. 2026. "Proposal: bound thinking with a token budget (think: N, effort levels,
PARAMETER think_budget)." Ollama issue #17561 (opened ~2026-08). GitHub.
https://github.com/ollama/ollama/issues/17561.
Claims: Ollama has no thinking budget; unbounded thinking can return no answer (Gemma-4:
7,208 thinking chars / 0 content vs 614 / 6,186 at budget 256); proposes using llama.cpp's
reasoning-budget sampler. Status: open, no maintainer response. Credibility: user proposal,
measurements on a pruned non-gpt-oss model; useful as status evidence only.

[A7] Wilkin, Piotr (pwilkin). 2026. "reasoning-budget: proper handling ... --reasoning-budget-
message." llama.cpp PR #20297, merged 2026-03-11. GitHub.
https://github.com/ggml-org/llama.cpp/pull/20297.
Claims: real token budget on the reasoning block via a delayed grammar; optional message
before the forced close; reviewer test: budgets 400-1000 reached ~89% with a budget message,
"terrible" 79% without. Credibility: primary engineering record; the quality numbers are an
informal PR-thread test on unspecified models; gpt-oss/harmony support not stated.

[A8] wparuch. 2026. "--no-thinking should inject Harmony channel-skip tokens for GPT-OSS
models." rapid-mlx issue #1067. GitHub. https://github.com/raullenchai/rapid-mlx/issues/1067.
Claims: on gpt-oss-20b, a raw completion prompt ending in an empty analysis message plus
`<|start|>assistant<|channel|>final<|message|>` gives a clean final answer with zero
reasoning tokens; the same tokens placed in chat `content` are escaped and do not work.
Credibility: single user test on a different server (MLX); corroborates the mechanism, not
Ollama behaviour.

[A9] goose project. 2026. "Reasoning models produce empty content: max_tokens shared between
reasoning_content and content." Issue #11142. GitHub.
https://github.com/aaif-goose/goose/issues/11142.
Claims: on OpenAI-compatible servers including Ollama, reasoning and answer share one
token cap; a long trace yields `finish_reason: length` and empty content (a silent failure).
Credibility: user report; matches our own #1317 symptom.

[A10] Lin, Shuyi, Tian Lu, Zikai Wang, Bo Wen, Yibo Zhao, and Cheng Tan. 2025. "Quant Fever,
Reasoning Blackholes, Schrodinger's Compliance, and More: Probing GPT-OSS-20B."
arXiv:2509.23882.
Claims: GPT-OSS-20B "often repeats itself in its chain-of-thought, falling into loops it
cannot escape"; with greedy decoding 81% (162/200) of tested prompts looped; top-1 token
probability approaches 1 after ~100 tokens; larger batch sizes increase it. Credibility:
red-team write-up (Kaggle) on jailbreak prompts, not code review; small samples; but the
only direct study of gpt-oss-20b looping and decoding temperature. Relevance high because
vibey reviews at temperature 0 [D-ctx].

## B. Reasoning-length control and forced answers

[B1] Muennighoff, Niklas, Zitong Yang, Weijia Shi, et al. 2025. "s1: Simple Test-Time
Scaling." arXiv:2501.19393.
Claims: budget forcing = append the end-of-thinking delimiter (optionally "Final Answer:")
at a token cap; gives perfect length control; at small budgets accuracy collapses (AIME24
3.3% at 1,024 forced tokens vs 30% at 2,048, Table 12); prompting a token limit alone is not
obeyed. Credibility: peer-reviewed-level, widely replicated; model is a fine-tuned Qwen-32B,
tasks are math.

[B2] Wu, Tsung-Han, Mihran Miroyan, David M. Chan, Trevor Darrell, Narges Norouzi, and
Joseph E. Gonzalez. 2026. "Are Large Reasoning Models Interruptible?" ICML 2026;
arXiv:2510.11713.
Claims: GPT-OSS-20B (high) behaves almost as an "anytime" model under hard interrupts
(accuracy rises with budget used); early interrupts cause "reasoning leakage" (answers up to
10x longer); "speed up" instructions cause "panic" (premature stop, up to 30% accuracy drop;
GPT-OSS-20B panic 30.7%). Credibility: strong venue, includes our exact model; math and
LiveCodeBench, not review.

[B3] Wang, Hanyang, and Mingxuan Zhu. 2026. "The Detection-Extraction Gap: Models Know the
Answer Before They Can Say It." arXiv:2604.06613.
Claims: 52-88% of CoT tokens come after the answer is recoverable; but forcing an answer
early ("Therefore, the final answer is") fails on ~42% of recoverable cases at a 10% prefix;
the gap shrinks to <5 pp by 70% of the trace; GPT-OSS-120B shows the largest early gap
(70 pp); naive forced early exit costs 41-62 pp. Credibility: preprint, two authors, careful
controls; math/GPQA/HumanEval; implication: force late, not early.

[B4] Rodionov, Gleb, Roman Garipov, and George Yakushev. 2026. "Reasoning Shift: How Context
Silently Shortens LLM Reasoning." COLM 2026; arXiv:2604.01161.
Claims: irrelevant or extra context shortens reasoning up to 74% and lowers accuracy
(gpt-oss-120b IMOAnswerBench 73.8 -> 64.0 with long input; GPQA 78.3 -> 57.6); prompting for
"max effort" does not fix it; solving two tasks in one prompt also hurts. Credibility:
strong venue; includes gpt-oss-120b; synthetic distractor setups.

[B5] Chen, Xingyu, Jiahao Xu, Tian Liang, et al. 2024. "Do NOT Think That Much for 2+3=? On
the Overthinking of o1-Like LLMs." arXiv:2412.21187. INC-A.
Claims: o1-like models spend excess tokens on easy problems; proposes self-training to cut
it. Credibility: widely cited; training-based remedy (not applicable without fine-tuning).

[B6] Sui, Yang, et al. 2025. "Stop Overthinking: A Survey on Efficient Reasoning for Large
Language Models." arXiv:2503.16419. INC-A.
Claims: taxonomy of model-, output- and prompt-based length control. Credibility: survey,
context only.

[B7] Gema, Aryo Pradipta, et al. 2025. "Inverse Scaling in Test-Time Compute."
arXiv:2507.14417. INC-A.
Claims: on constructed tasks longer reasoning lowers accuracy (distraction, overfitting to
framing). Credibility: Anthropic-affiliated; constructed tasks.

[B8] Zeng, Zhiyuan, et al. 2025. "Revisiting the Test-Time Scaling of o1-like Models."
arXiv:2502.12215. INC-A.
Claims: for the same question correct CoTs are often shorter than incorrect ones; parallel
sampling scales better than sequential. Credibility: preprint; consistent with B3/B9.

[B9] Ghosal, Soumya Suvra, et al. 2025. "Does Thinking More Always Help? Mirage of Test-Time
Scaling in Reasoning Models." arXiv:2506.04210. INC-A.
Claims: extended thinking first helps then hurts; parallel thinking with majority vote is up
to 20% better at equal budget. Credibility: preprint.

[B10] Yang, Chenxu, et al. 2025. "Dynamic Early Exit in Reasoning Models." arXiv:2504.15895.
INC-A. Claims: confidence-triggered early exit cuts CoT 19-80% with +0.3-5% accuracy.
Credibility: preprint; needs token logprobs at transition points (possible with Ollama
logprobs, untested).

## C. Long input / context dilution

[C1] Du, Yufeng, Minyang Tian, et al. 2025. "Context Length Alone Hurts LLM Performance
Despite Perfect Retrieval." arXiv:2510.05381.
Claims: 13.9-85% degradation as input grows even with perfect retrieval, whitespace padding,
or masked padding; a "recite evidence, then solve on the short prompt" step recovers much of
it (Mistral GSM8K at 26k: 35.5% -> 66.7%). Credibility: controlled; older/smaller models.

[C2] Liu, Nelson F., et al. 2023. "Lost in the Middle: How Language Models Use Long
Contexts." arXiv:2307.03172; TACL 2024. INC-A. Claims: U-shaped accuracy by evidence
position. Credibility: foundational; older models.

[C3] Kumar, Deepak. 2026. "SWE-PRBench: Benchmarking AI Code Review Quality Against Pull
Request Feedback." arXiv:2603.26130.
Claims: 8 frontier models detect 15-31% of human-flagged issues on diff-only prompts; all
degrade monotonically when file content / test signatures are added (A>B>C) even within
2,000-2,500 tokens; a 200-token LLM "key changes summary" before the diff was the
highest-return addition and reduced hallucination. Credibility: single independent author,
judge validated at kappa 0.75; 100-PR sample; plausible but not yet replicated.

[C4] Bradford, Nick. 2025. "How we built Ellipsis." Blog. https://www.nsbradford.com/blog/
how-we-built-ellipsis. INC-A. Claims: "noticeably more hallucinations when more than half
the context is filled"; decomposes review into many small comment generators plus filters.
Credibility: vendor engineering blog; heuristic, no data.

## D. Code review: industrial systems and vendors

[D1] Qodo (formerly CodiumAI). 2026. "PR-Agent" source and docs (pr_agent/algo/
pr_processing.py; settings/configuration.toml; docs/core-abilities/compression_strategy.md).
GitHub, commit 2b73b361cf (2026-10-01). https://github.com/qodo-ai/pr-agent.
What it does: sorts files by repo language then by token count; drops deletion-only hunks and
lists deleted files by name; adds patches until a soft buffer (1,500 tokens) below
`max_model_tokens` (default 32,000), then lists the rest as "other modified files" (not
reviewed); `large_patch_policy = "clip"|"skip"`; dynamic context extends a hunk up to 10 lines
back to its enclosing function; opt-in `enable_large_pr_chunking` with `max_number_of_calls=3`;
`/improve` extended mode chunks (3 calls, parallel) and always runs a self-reflection call that
scores each suggestion 0-10 and drops low scores; coverage footer reports omitted files.
Credibility: primary source code; open source; model-agnostic via LiteLLM (Ollama possible);
no published accuracy numbers from Qodo itself.

[D2] Cihan, Umut, Vahid Haratian, Arda Icoz, et al. 2024. "Automated Code Review In
Practice." arXiv:2412.18531 (Beko + Bilkent).
Claims: PR-Agent on GPT-4-32K across 4,335 PRs; 73.8% of bot comments labelled resolved;
mean PR closure time rose from 5h52m to 8h20m; complaints of faulty / out-of-scope comments.
Credibility: industry case study; one company; labels partly policy-driven.

[D3] CodeRabbit. 2023. "ai-pr-reviewer README" (archived OSS action) and "How we built a
cost-effective Generative AI application" (blog, 2023-12-22).
https://github.com/coderabbitai/ai-pr-reviewer ;
https://www.coderabbit.ai/blog/how-we-built-cost-effective-generative-ai-application.
Claims: light model summarises each file diff and triages trivial vs complex in the same
prompt; heavy model reviews each non-trivial file; skipping trivial changes "save[s] almost
50%" of cost; incremental review uses summary comparison to skip unchanged files.
Credibility: vendor; mechanism credible and documented in OSS code (2023 era); current
product is closed.

[D4] CodeRabbit. 2026. Documentation: plans, auto-review, Change Stack.
https://docs.coderabbit.ai. Claims: 150-300 files per review by plan (after path filters);
incremental review per push; LLM-grouped "cohorts/layers" of a PR. Credibility: vendor
docs; limits authoritative, quality claims not.

[D5] GitHub. 2025-2026. "Copilot code review: Better handling of large pull requests"
(changelog 2025-07-02); "...Resolution reasons and expanded capabilities" (changelog
2026-08-27); "About GitHub Copilot code review" (docs); Gopu, Ria, and David Apirian. 2026.
"60 million Copilot code reviews and counting." GitHub Blog, 2026-03-05.
Claims: a 300-file / 20,000-line limit existed and was removed in Aug 2026; excludes lockfiles,
logs, SVG; Lite vs Balanced (higher-reasoning) modes; agent "catches issues as it reads, not
just at the end" because waiting to the end "often led to 'forgetting' early discoveries";
plans its review for long PRs; says nothing on 29% of reviews; a stronger reasoning model gave
+6% positive feedback at +16% latency. Credibility: vendor; mechanisms plausible; no
recall/precision disclosed.

[D6] Google. 2026. "Review GitHub code using Gemini Code Assist." Google for Developers.
https://developers.google.com/gemini-code-assist/docs/review-repo-code. INC-A.
Claims: quotas, excludes `.github/workflows`. No large-diff mechanism disclosed.

[D7] Vijayvergiya, Manushree, Malgorzata Salawa, Ivan Budiselic, et al. 2024. "AI-Assisted
Assessment of Coding Practices in Modern Code Review" (AutoCommenter). AIware '24;
arXiv:2405.13565.
Claims: per-file T5 model with 2,048-token context ("suffices for only around 200 lines"),
input truncated if longer; per-URL confidence thresholds; filtering comments on unchanged
lines (80% of raw predictions were on unchanged lines); beam search n=4; ~40% estimated
resolution; useful ratio >80% after suppression. Credibility: Google, peer-reviewed workshop;
precision-first design; best-practice comments, not bugs.

[D8] Frommgen, Alexander, and Lera Kharatyan. 2023. "Resolving Code Review Comments with ML."
Google Research Blog, 2023-05-23. https://research.google/blog/resolving-code-review-
comments-with-ml/. Claims: 52% of comments addressed at a tuned 50% precision; serving-time
filtering trades quantity for quality. Credibility: vendor-internal but Google research;
different task (edit suggestion).

[D9] Adams, Chris, Arjun Singh Banga, et al. 2026. "Automating Low-Risk Code Review at Meta:
RADAR, Risk Calibration, and Review Efficiency." arXiv:2605.30208.
Claims: funnel = eligibility gates -> static heuristics -> ML Diff Risk Score -> LLM review
(auto-accept only if all changes fall into "safe" classes such as refactor without behaviour
change, dead-code removal, formatting, at confidence >= 8/10) -> deterministic validation;
deterministic codemods bypass per-diff AI review; 535K+ diffs reviewed; revert rate 1/3 and
incident rate 1/50 of non-RADAR diffs. Credibility: Meta authors; observational (selection
bias: low-risk diffs are by construction safer); strong evidence that risk triage is
deployable, weak evidence on recall.

[D10] Sun, Tao, Jian Xu, Yuanpeng Li, et al. 2025. "BitsAI-CR: Automated Code Review via LLM
in Practice." arXiv:2501.15134 (ByteDance).
Claims: two-stage RuleChecker -> ReviewFilter (both fine-tuned); filter raised precision
57.0% -> 65.6% (recall 45.5% -> 39.8%); "conclusion-first" filter prompt gave 77.1%
precision at 1.7 s vs 31 s for reasoning-first; online precision 75%; 99% of review samples
<8,192 tokens. Credibility: industry, fine-tuned 32k model; filter design transferable,
numbers not.

[D11] Tantithamthavorn, Kla, Yaotian Zou, Andy Wong, et al. 2026. "RovoDev Code Reviewer: A
Large-Scale Online Evaluation of LLM-based Code Review Automation at Atlassian." ICSE-SEIP
'26; arXiv:2601.01129.
Claims: zero-shot Claude 3.5 Sonnet + LLM-judge factual check + ModernBERT actionability
filter; 54k comments, 38.7% code-resolution rate vs 44.5% for humans; PR cycle time -30.8%;
the LLM-judge factual check had "minimal impact" while the trained actionability filter
added 15-20 pp. Credibility: strong venue, one year of production data; filter needs
labelled history.

[D12] Ramesh, Shweta, Joy Bose, et al. 2025. "Automated Code Review Using Large Language
Models at Ericsson: An Experience Report." arXiv:2507.19115.
Claims: self-hosted Llama/Code Llama 7-13B; context = changed lines + tree-sitter-extracted
enclosing method; survey of 8-9 experts mixed. Credibility: small preliminary study; relevant
as a sovereign/local precedent, not as performance evidence.

[D13] Tuli, Sneha. 2025. "Enhancing Code Quality at Scale with AI-Powered Code Reviews."
Microsoft Engineering blog, 2025-07-14. INC-A. Claims: >90% of PRs, 600K PRs/month,
10-20% median completion-time improvement in 5,000 repos. Credibility: vendor-internal
blog; no accuracy data.

[D14] Graphite. 2024. "Introducing Graphite Reviewer." Blog, 2024-09-30. INC-A. Claims
"<3% false-positive rate across tens of thousands of code changes". Credibility: vendor
claim, definition of FP undisclosed; treat as unverified.

[D15] Greptile (via ZenML LLMOps database). 2024. "Improving AI Code Review Bot Comment
Quality Through Vector Embeddings." INC-A. Claims: 79% of comments were nits; filtering by
embedding similarity to past downvoted comments raised addressed rate 19% -> 55%.
Credibility: vendor talk summarised by third party; needs feedback history we lack.

[D16] Bito. 2026. "AI Code Review Agent - GitHub guide." docs.bito.ai. INC-A. Claims:
automatic review up to 5,000 changed lines; larger needs `/review full`; incremental review.
Credibility: vendor docs (limits only).

[D17] Aider. 2026. "Repository map." aider.chat/docs/repomap.html.
Claims: tree-sitter symbol map ranked by a graph algorithm over file dependencies, budget
`--map-tokens` default 1,000. Credibility: primary docs; a context-selection precedent.

## E. Benchmarks and evaluation methodology

[E1] Zeng, Zhengran, Ruikai Shi, et al. 2026. "SWR-Bench: Assessing LLM Performance in
Real-World Code Review Comment Generation." FSE 2026; arXiv:2509.01494.
Claims: 1,000 PRs; best F1 ~19-21%; precision is the binding constraint (several FPs per
PR); recall falls from 38.4% (1 issue) to 8.9% (>=5 issues) while precision stays ~30-44%;
reasoning models do better; five runs of one model overlap on only 27 found issues;
"Multi-Review" self-aggregation at n=10 raised F1 +43.7% and recall +118.8%, diminishing past
n=5; Qwen-2.5-7B/32B also gain. Credibility: strong venue, judge ~90% agreement with humans.

[E2] Zhang, Yuntong, Zhiyuan Pan, Imam Nur Bani Yusuf, et al. 2026. "Code Review Agent
Benchmark" (c-CRAB). arXiv:2603.23448.
Claims: human review comments converted into executable tests (fail before, pass after a
coding agent applies the review); PR-Agent, Devin, Claude Code, Codex together solve ~40%;
agents favour robustness/testing, miss design/maintainability. Credibility: NUS + SonarSource;
strongest oracle design found; Python-centric.

[E3] Kumar, Shivam Pankaj, Swati Bararia, and Kislay Raj. 2026. "Bigger Isn't Always
Better: A Comparative Evaluation of LLMs for Automated Code Review." arXiv:2606.15689.
Claims: synthetic mutation-injected bugs overstate capability (F1 0.847 synthetic vs 0.066
on real PRs); F1 by diff size 0.66 (<10 lines) / 0.80 (10-50) / 0.07 (50-150) / 0.04
(150-600); union-of-models ensembles lower F1. Credibility: weak-moderate: 150 samples (50
real, 14 in the largest bucket), ground truth auto-extracted, a vendor co-author, judge
from same family; directionally consistent with E1/E5.

[E4] Klieber, William, David Svoboda, Lori Flynn, and Ruben Martins. 2026. "Using LLMs to
Adjudicate Static-Analysis Alerts with Error Reduction Techniques." arXiv:2607.09979 (CMU
SEI).
Claims: gpt-oss-20b adjudicating single alerts reaches ~96-99% recall and ~96-97% specificity
on Juliet/SV-COMP; with a consistency check (N runs, threshold) plus an "LLM reasoning
evaluation" step it reaches 100%/100% on SV-COMP and >=96% specificity on FormAI; plain
majority voting is a modest gain; LRE applied only when runs disagree (43% of alerts for
gpt-oss-20b). Credibility: government-lab authors, careful CIs; adjudication of a given
claim, not open-ended review; Juliet memorisation risk acknowledged. Most direct evidence
that gpt-oss-20b is a reliable verifier on small inputs.

[E5] Authors not verified (Singapore Management University). 2026. "PRWeaver: Evaluating LLM-Based Code Auditors against
Long-Horizon Malicious Pull Requests." arXiv:2608.02693. INC-A.
Claims: detection of planted malicious changes is 50-60% when PRs are reviewed one by one but
16-22% when 24 PRs are reviewed as one window; interleaving benign and malicious changes in
the active context hides them. Credibility: preprint, adversarial setting; strong support for
small review units.

[E6] Pereira, Kristen, et al. 2026. "CR-Bench." arXiv:2603.11078; Martian AI. 2026. "Code
Review Bench." https://codereview.withmartian.com. INC-A (cited via E3). Credibility:
third-party leaderboard; not read in full.

[E7] Alibaba / Nanjing University. 2026. "AACR-Bench." arXiv:2601.19494. INC-A. Claims:
expert-verified latent defects add 285% defect coverage over raw PR comments; context
granularity effects vary by model. Credibility: preprint.

[E8] Authors not verified (Tencent). 2025. "Towards Practical Defect-Focused Automated
Code Review." arXiv:2505.17928. INC-A. Claims: code slicing for context, multi-role LLM for
key-bug inclusion, a filter for false-alarm rate; 2x over standard LLM on real C++ merge
requests. Credibility: preprint, industrial; cite by arXiv id.

[E9] Authors not verified. 2026. "Refute-or-Promote: An Adversarial Stage-Gated Multi-Agent
Review Methodology." arXiv:2604.19049. INC-A. Claims: adversarial refutation killed ~79-83%
of LLM-proposed defect candidates; ten reviewers unanimously endorsed a non-existent bug that
only an empirical test killed. Credibility: preprint; cite by arXiv id;
qualitative but instructive about correlated false positives.

## Context file (not a publication)

[D-ctx] vibey. 2026. `src/vibey_tools/gh/vibey_gh/config.py`, sovereign review fallback
settings (read 2026-10-01): context_window 65,536; reasoning_reserve_tokens 16,384 sent as
`num_predict`; `think` empty (model default = medium); max_chunks 6; split_added_hunks; and
a comment stating requests run "at temperature 0". Used only to tie evidence to the setup.
