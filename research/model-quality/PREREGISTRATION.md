# Preregistration: which open-weights model should drive the sovereign BUILD loop

- **Registered:** 2026-11-10, before any quality outcome of any model below was observed here.
  The commit that adds this file is the registration.
- **Code under study:** `qwenloop run` at `010ebc70` (develop), backend `openai-compat` on Ollama.
- **Host:** Apple M5, 24 GiB unified memory, one model loaded at a time, Ollama 0.40.x.
- **Supersedes nothing yet.** ADR-0099 (Heretic v2 of gpt-oss-20b as default) stands until this
  study's decision rule selects otherwise and a new ADR says so.

What was already known (and so is not a finding): one task (slugify), 3 to 5 trials, `gpt-oss:20b`
solved 1 of 3 (`docs/architecture/evidence/model-build-benchmark-2026-10-23.md`). Heretic v2 has
never been pulled or measured on this host. Every other harness in the repository measures speed.

## 1. Question

Which model that is OSI-licensed, fits in 24 GiB at 32,768 tokens of context, and drives the real
`qwenloop` runner, solves the most BUILD tasks whose verdict a hidden test suite decides?

## 2. Hypotheses

- **H1.** Solve rate differs between models by more than trial noise (Wilson 95% intervals do not
  all overlap).
- **H2.** Heretic v2 of a model solves within 0.10 (absolute) of that model's stock build.
  H0: it differs by more. Tested for every finalist that has a Heretic v2 build.
- **H3.** Tool-calling reliability (the share of turns whose tool call parses and runs) predicts
  solve rate across models.

## 3. Candidate field (dated 2026-11-10; the field moves monthly)

Sources: Ollama search (`ollama.com/search?c=tools&o=newest`) and Hugging Face search for
`heretic`, both fetched 2026-11-10. Third-party ranking blogs were read and not relied on.
A model enters the run only after §3.2 is satisfied.

### 3.1 Starting list

| Key | Tag | Why it is here |
|---|---|---|
| `heretic-v2` | `hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE` | Current default (ADR-0099) |
| `gpt-oss-stock` | `gpt-oss:20b` | Baseline; reproduces October slugify first |
| `qwen3-14b` | `qwen3:14b` | Present on host; optional model in `minimum_specs.toml` |
| `qwen25-coder-14b` | `qwen2.5-coder:14b` | Previous default; present on host |
| `qwen38-27b` | Ollama `qwen3.8:27b` (to confirm) | Named in `local-model-catalogue.md`; reported 18 GB |
| `qwen36-27b` | to confirm | Named in `local-model-catalogue.md` |
| `devstral-small` | Ollama devstral small (to confirm) | Agentic coding specialist |
| `deepseek-coder` | newest Ollama build that fits (to confirm) | Coding family |
| `mimo-v2.6-9b`, `nemotron-3.5-bolt`, `bonsai-2` | Ollama | Newly listed small agentic models |
| `gemma4-26b` | `gemma4:26b` | Non-OSI **reference point only**; never eligible as default |

Excluded without a run: cloud-only tags; anything over 24 GiB resident at 32k context
(`qwen3.6-35b-a3b` and `flint` 40b are expected to fail the fit screen and are measured by it, not
assumed); models with no tool-calling that `OllamaModelProbe` rejects.

### 3.2 Entry rules

1. The licence is read from the model card or `LICENSE` at pull time and recorded with its SPDX id
   and URL. A licence that cannot be read makes the model non-OSI for this study.
2. `OllamaModelProbe` shows tool-calling. A model without it is recorded as screened out.
3. A memory sweep at `num_ctx 32768` shows resident size at most 20 GiB (headroom for the OS and
   the runner), measured with `MemoryProbe` and `ollama ps`.
4. Finalists (the top three by solve rate, and always the current default) that have a Heretic v2
   build are also run on it. Heretic builds are matched to the exact base revision where the
   repository says so, and a mismatch is recorded.

## 4. Tasks

About 30 tasks under `research/model-quality/tasks/`, Python and TypeScript, four tiers:

| Tier | Count | Shape |
|---|---|---|
| T1 single function | 8 | one new file, pure function |
| T2 multi-file feature | 8 | two to four files, an interface and a caller |
| T3 bug fix from a failing test | 8 | a repository with one failing visible test |
| T4 refactor, behaviour preserved | 6 | rename or extract, hidden tests pin behaviour |

Each task directory holds `plan.md` (what the model sees), `seed/` (the starting repository),
and `hidden/` (tests the model never sees, copied in only at scoring time). **Scoring** is the
way `build_verify_handler` scores a work item: hidden tests pass, `ruff check` is clean, and
`mypy` (Python) or `tsc --noEmit` (TypeScript) passes. A trial **solves** only when all three do.
The model's own tests passing counts for nothing.

Task authoring is frozen before the first scored trial. Tasks are split before any run into a
screening set (6 tasks, one tier-mix) and a confirmation set (the rest) by
`random.Random(20261110)`. The screening set decides which models earn the full run.

## 5. Procedure

- Five trials per model per task, a fresh git repository each, `--max-turns 25`, wall cap 420 s
  per trial, sampling at the runner's defaults.
- One derived Ollama tag per model with `num_ctx 32768`, built by the harness from a generated
  Modelfile. A model run at Ollama's default context is invalid (the October run showed why).
- A quiet-host gate from `minimum_specs.py` before each trial; a trial that starts on a busy host
  is not run, not discarded afterwards.
- Resumable through `StepJournal`; results appended to a digest-chained ledger in the
  `CanaryLedger` pattern; Wilson intervals as in `review_canary.py`.
- **Calibration gate.** Before the full run the harness must reproduce the October slugify result
  for stock `gpt-oss:20b` within its stated limits (1 of 3 correct, 15 tool calls on average).
  If it cannot, the harness is wrong, and no model result is reported.

## 6. Decision rule

1. Drop every model that fails §3.2.
2. Rank the rest by solve rate over the confirmation set.
3. Speed breaks a tie only where Wilson 95% intervals overlap.
4. The default is the best-ranked model whose licence is OSI-approved. A non-OSI model is
   reported and never selected.
5. If the winner is not the current default, a new ADR supersedes ADR-0099, and one pull request
   moves every pin together. If it is, the same pull request still fixes the pins that drifted
   to stock `gpt-oss:20b`.

## 7. Outcomes recorded

Solve rate with Wilson interval; per-tier solve rate; turns, tool calls, tokens, seconds per
trial; tool-call parse rate; peak resident memory; failure class (no files, wrong behaviour, lint,
type, turn cap, timeout, crash). Runner crashes are reported as invalid trials with the cause,
never hidden, and rerun after the fix.

## 8. Threats

- One host, one runner version. Results say nothing about other hardware.
- Task authors are the study's authors; hidden tests may favour a style. Mitigation: tests assert
  behaviour only, and all tasks are published.
- Five trials per cell bounds precision; intervals are reported, and no ranking is claimed inside
  an overlap.
- Community Heretic builds are not reproducible from the tool's output alone; the exact repository,
  revision and quantization are recorded, and a missing revision is a recorded limit.
- Rankings published by third parties informed the candidate list only.
