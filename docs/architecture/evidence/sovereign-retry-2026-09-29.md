# Sovereign DESIGN and DECOMPOSE on gpt-oss:20b: before and after the length-aware retry

- Object: how often `GptossloopDesignProvider.batch` (the `design.interview` step) and `GptossloopWorkPlanProducer.decompose` (`build.decompose`) return a usable answer from gpt-oss:20b, before and after branch `fix/sovereign-length-aware-retry`
- Host: the operator's macOS 26.6.2 workstation, ollama 0.34.4, `gpt-oss:20b` digest `17052f91a42e`; no other model request was in flight during either run
- Ceilings: the defaults, no fit record (`VIBEY_OLLAMA_CONTEXT`, `VIBEY_OLLAMA_OUTPUT`, `VIBEY_OLLAMA_FIT` unset): context ceiling 8192, output 2048, temperature 0, JSON mode. The `num_ctx` / `num_predict` / `think` actually sent are recorded per exchange in the JSON records
- Cutoff: before 2026-09-29T07:36:40Z to 08:04:42Z; after 2026-09-29T08:04:55Z to 08:37:39Z
- Instrument: `scripts/sovereign_retry_experiment.py --runs 10 --workloads design,decompose --replay-ledger <export>`, which calls the production producers over `OllamaChatClient.from_environment` with only a recording transport added
- Records: [`sovereign-retry-2026-09-29-before.json`](sovereign-retry-2026-09-29-before.json), [`sovereign-retry-2026-09-29-after.json`](sovereign-retry-2026-09-29-after.json)

## Workloads

- `design.interview`: 10 synthetic runs, cycling the seven DESIGN stages over three one-paragraph briefs (10 distinct prompts).
- `design.interview (production replay)`: the DESIGN-phase ledger of the project whose `design.interview` job had failed 11 attempts with `KeyError: 'question_id'` (GitHub issue #133's project, 34 events), asked for the stage it was stuck on (`walking_skeleton`), 10 times. The ledger export is not committed.
- `build.decompose`: 10 runs cycling three synthetic specs of 3 to 5 criteria (3 distinct prompts).

## Results

| workload | N | ok | empty content (done_reason) | schema violation | first call cut short (`length`) | mean calls | mean latency |
|---|---|---|---|---|---|---|---|
| design.interview, before | 10 | 0 | 0 | 10 (`KeyError: 'question_id'`) | 0 | 1.0 | 20.7 s |
| design.interview, after | 10 | **10** | 0 | 0 | 0 | 1.0 | 25.1 s |
| production replay, before | 10 | 0 | 0 | 10 (`questions must be a list`) | 0 | 1.0 | 24.4 s |
| production replay, after | 10 | **10** | 0 | 0 | 0 | 1.0 | 77.8 s |
| build.decompose, before | 10 | 0 | 7 (`length` x7) | 3 (`verification must be an object`) | 7 | 1.7 | 123.1 s |
| build.decompose, after | 10 | **10** | 0 | 0 | 10 (4 empty, 6 truncated JSON) | 2.0 | 93.5 s |

What the before run shows:

- Every DESIGN failure was a shape failure, not a transport one: in JSON mode the prompt carried no schema, so the model chose its own key names. The synthetic runs reproduced the production `KeyError: 'question_id'`; the production replay put the questions under another key.
- 7 of 10 decompose runs spent the whole 2048-token budget reasoning (`done_reason: length`, empty content, a full `thinking` channel). The existing empty-reply retry resent the same budget in the same mode, and every one of the 7 failed identically on the retry -- the production `Ollama response carried empty message content`.

What the after run shows:

- Stating the schema in the prompt removed every shape failure; no answer needed the re-ask (mean calls 1.0 for DESIGN), so the re-ask path is proven by unit tests only, not by this run.
- Every decompose first call was cut short at 2048 tokens (the schema lengthens the prompt and the answer), and every one was completed by the single widened retry: `num_predict` 4096 within `num_ctx` 4931-5028, `think: "low"`. The retries used 446-907 output tokens, so the lighter reasoning, not the larger budget, is what made room; the two levers were not separated.

## Not measured

- Determinism: at temperature 0 an unchanged prompt repeats its answer (the replay's 10 runs and each spec's repeats returned identical token counts), so N counts runs, not independent samples: 10 distinct DESIGN prompts, 1 replay prompt, 3 decompose prompts.
- The latency cost of the stated schema on a large ledger (24 s to 78 s on the replay) was measured once on one host; whether it matters against the worker's 900 s timeout was not tested beyond this.
- `design.research` and `design.synthesize` go through the same `ValidatedAsk` after the change and were not replayed live.
- The `OutputBudgetExhausted` path (a second cut-short reply) did not occur live; it is covered by unit tests.
- A fitted ceiling (`VIBEY_OLLAMA_FIT`), other models (qwen3:14b accepts `think: "low"` but thinks regardless) and other hosts.
