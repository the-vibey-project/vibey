## Title
feat(ledger): the billing projection keeps the local lane's per-turn timings, so the billing ledger carries both lanes

## Why
Issue #134, "Proposed child issues" 7, and Scope 3 "Cost `C(o)`: the paid lane in dollars
(ledger `cost_usd`), and the local lane in generation-seconds (qwenloop timing), shown
separately and together" (rewrite `issue-audit/updates/134.md`). This is cost accounting only.
It is lane 1 of 4:
- this lane: the conductor exports the local lane's timings;
- `-p2`: vibey-gh reads them as generation-seconds;
- `-p3`: the estimate report shows cost;
- `-p4`: `vibey-gh estimate` reads the billing ledger.

Sub-doctrine 8.a (`src/vibey_tools/gh/docs/doctrines.md:99-118`) makes the local lane's cost
real. 8.g (`:316-324`) measures it.

qwenloop now records each turn's timing (lane `qwenloop-run-telemetry`, #382, landed as
`d76c2e20`). Its `turn.completed` event carries three timing fields
(`src/vibey_runners/qwen/src/qwenloop/application/runner.py:323-335`):
- `duration_ms`, which includes the turn's tool runs;
- `model_ms`, the time until the model answered;
- `server_timings`, only when llama-server reports them. That is `prompt_ms`, `predicted_ms`
  and the counts (`src/vibey_runners/qwen/src/qwenloop/infrastructure/inference.py:237-250`).

The conductor stores these fields as the payload of the ledger's `TurnCompleted`:
- qwenloop's events are flat, so every key except the type and the timestamp becomes the
  payload (`src/vibey/infrastructure/engines/loop_process_adapter.py:494-506`);
- `turn.completed` maps to `TURN_COMPLETED` (`src/vibey/infrastructure/engines/loop_events.py:207-214`);
- the payload passes through unchanged (`src/vibey/infrastructure/engines/tailer.py:83-97`).

But the billing projection keeps only `cost_usd` of a `TurnCompleted`
(`src/vibey/domain/publication_policy.py:392-403`, at `:394`). So the billing ledger the
forecast reads (`roadmap-134-billing-ledger-export`) holds no local-lane time at all.

## Required behaviour
1. In `BILLING_ALLOWLIST` (`publication_policy.py:392-403`), the `TurnCompleted` entry (`:394`)
   becomes `EventKind.TURN_COMPLETED: frozenset({"cost_usd", "model_ms", "server_timings"})`.
   Nothing else in the mapping changes.
2. Extend the comment above it (`:385-391`) with one sentence: "`model_ms` and
   `server_timings` are the local lane's per-turn timings (qwenloop's `turn.completed`,
   #382), kept so the billing ledger carries generation-seconds beside dollars (#134)."
3. `server_timings` is a mapping of numbers. The policy keeps a nested mapping whole and
   scrubs only its strings (`_scrub_mapping`, `:362-375`), so it is published as recorded.

## Where to change
- `src/vibey/domain/publication_policy.py` (use `edit_file`: one entry, one comment sentence).
- Append to `tests/domain/test_publication_policy.py`. Do not rewrite it.
- Append to `tests/cli/test_billing_ledger_export.py`, which lane
  `roadmap-134-billing-ledger-export` created. Reuse its `_seed` pattern.
- No other file.

## Acceptance criteria
- [ ] A `TurnCompleted` with payload
      `{"model_ms": 900, "duration_ms": 5000, "server_timings": {"prompt_ms": 120.5, "predicted_ms": 800.0, "prompt_n": 10}, "text": "answer"}`
      publishes through `BILLING_POLICY` as
      `{"model_ms": 900, "server_timings": {"prompt_ms": 120.5, "predicted_ms": 800.0, "prompt_n": 10}}`.
- [ ] `test_billing_projection_is_explicit_and_keeps_only_metered_fields`
      (`tests/domain/test_publication_policy.py:361-379`) passes unchanged.
- [ ] The public projection is unchanged: `TurnCompleted` is still engine chatter there,
      withheld whole (`ENGINE_CHATTER`, `:72-75`).
- [ ] 100% branch coverage of `src/vibey/domain/`.

## Tests to write first (TDD)
Append to `tests/domain/test_publication_policy.py` (reuse its `_event`, `:45-64`):
- `test_billing_projection_keeps_local_turn_timings`: the first acceptance criterion via
  `BILLING_POLICY.apply((event,)).records[0].payload`, with `kind=EventKind.TURN_COMPLETED`,
  `provenance=Provenance.AGENT` and `engine_id=EngineId.QWENLOOP`.
- `test_the_public_policy_still_withholds_local_turn_timings`: the same event through
  `DEFAULT_POLICY.decide(event)`. `decision.record is None` and
  `decision.withheld is WithheldReason.ENGINE_CHATTER` (`PublicationDecision`, `:245-250`).

Append to `tests/cli/test_billing_ledger_export.py`:
- `test_the_billing_ledger_carries_local_turn_timings`: seed one project whose ledger holds a
  `TURN_COMPLETED` for `EngineId.QWENLOOP`, with the payload above. Export with
  `run(pid, None, billing=True)`. The one `TurnCompleted` record line in the file, read with
  `json.loads`, has a `payload` equal to the published payload above.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_publication_policy.py tests/cli/test_billing_ledger_export.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Reading the timings in vibey-gh (`roadmap-134-cost-integral-p2`). Any change to qwenloop.
- Recording a generation duration for Ollama's OpenAI-compatible endpoint, which reports no
  `timings`. That is a qwenloop follow-up, named in `-p2`'s problem text.
- Publishing timings in the public shard. Docs, CHANGELOG. Do not push. Commit locally with
  the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
