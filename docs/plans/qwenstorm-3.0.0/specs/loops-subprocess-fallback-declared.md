## Title
feat(rotation): a paid selection in subprocess mode is declared on the ledger as PaidFallbackDeclared

ADR-0046 lane L13 (slug `loops-subprocess-fallback-declared`).

## Why
Draft ADR-0046 §2 (`specs/ADR-two-loops.md:125-126`): "Whenever the choice is paidloop, vibey
writes a `PaidFallbackDeclared` ledger event. It names every sovereign adapter in the pool and
why that adapter could not take the job … The event is written in both invocation modes. This
closes ADR-0038's *Bad* point 'the paid fallback is not yet declared' (8.a: 'declared loudly to
a human')." And §2's last paragraph (`:138`): subprocess invocation keeps "`preferred_tier` then
`select`, unchanged, plus the fallback declaration". Sub-doctrine 8.a
(`src/vibey_tools/gh/docs/doctrines.md:99-112`) and 7.c (`:82`) are the rules.

At integration `d3b4a388` the production BUILD selector, `SelectingEngineProvider.select_for`
(`src/vibey/application/engine_selection.py:206-248`), calls `select_engine` (`:226-231`),
records the selection (`:243-246`) and assigns the engine (`:247`); a paid choice leaves no
trace of why sovereign lost. This lane writes the declaration in subprocess mode, through the
`PhaseLedger` port (`src/vibey/application/interfaces/ledger.py:104-120`) with `Phase.BUILD`
(design sheet decision D10), using lanes `loops-weighted-candidates` and `loops-loop-selector`.

## Required behaviour
1. `SelectingEngineProvider.__init__` (`engine_selection.py:170-195`) gains two keyword
   parameters after `metrics`: `decisions: PhaseLedger | None = None` and
   `loop_selector: LoopSelectorInterface | None = None`. Exactly one of them set raises
   `ValueError("decisions and loop_selector are given together or not at all")`. Both are kept
   as one attribute `self._declaration: tuple[PhaseLedger, LoopSelectorInterface] | None`.
2. With neither set, `select_for` is **exactly today's**: it calls `select_engine` as `:226-231`
   does, and nothing is written. (This keeps `tests/application/test_engine_selection.py`,
   including `_SelectsAnEngineWithNoAdapter` at `:340-345`, which has only `select_engine`,
   passing unedited.)
3. With both set, `select_for` calls `weighted = await self._selector.weighted_candidates(job.project_id, inputs.requirement, allow_list=self._pool, affinity_engine=inputs.affinity)`
   and then `engine_id, _selection = await self._selector.select_from(weighted)` — the same
   inputs as today; a `NoEligibleEngine` from either becomes the same `CapacityDeferred` as
   `:232-233`. The adapter lookup, `record_selection`, the metric and `assign_engine`
   (`:234-247`) are unchanged.
4. **After `assign_engine`**, when `self._declaration` is set and
   `adapter.descriptor.tier is EngineTier.PAID`, it appends one event:
   `await decisions.append_event(job.project_id, job.cycle, job.id, EventKind.PAID_FALLBACK_DECLARED, PaidFallbackDeclaration(engine_id=engine_id.value, invocation="subprocess", sovereign=loop_selector.sovereign_exclusions(weighted)).to_payload())`.
   A sovereign selection writes nothing. A paid selection from a pool with no sovereign adapter
   still writes it, with an empty `sovereign_adapters` list: every paid choice is declared.
5. A failing append propagates (the worker turns it into a `VIBEY` failure, as for any handler
   error); the engine was already assigned, so a retry sees the same durable state (idempotent
   under replay: the next attempt selects and declares again, and the ledger keeps both — it is
   append-only).
6. `build_full_worker` (`src/vibey/bootstrap.py:341-391`) passes
   `decisions=PostgresReviewLedger(resources.ledger, phase=Phase.BUILD)` and
   `loop_selector=LoopSelector(descriptors=BY_ENGINE_ID)` to `SelectingEngineProvider`, so
   production declares from now on. `PostgresReviewLedger` writes provenance TRUSTED, no
   `engine_id` column value, and the engine in the payload (`src/vibey/infrastructure/db/review_ledger.py:34-58`).

## Where to change
Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` first. Both source files
are over 100 lines: `edit_file` only.

- `src/vibey/application/engine_selection.py` (403 lines):
  - imports: add `WeightedCandidates` to `from vibey.application.dto import EngineEvent, JobRecord`;
    add `LoopSelectorInterface` and `PhaseLedger` to the `from vibey.application.interfaces import (...)`
    list; `from vibey.domain.engine import ENGINE_ID_PARSER, EngineId, EngineTier, JobRequirement`;
    add `from vibey.domain.ledger import EventKind` and
    `from vibey.domain.loop_events import PaidFallbackDeclaration` (isort order).
  - `__init__`: the two parameters after `metrics: TelemetryMetrics | None = None,`, and at the
    end of the body:
    ```python
            if (decisions is None) != (loop_selector is None):
                raise ValueError("decisions and loop_selector are given together or not at all")
            # Sub-doctrine 8.a: a paid choice is declared loudly, with its reasons (ADR-0046 §2).
            self._declaration: tuple[PhaseLedger, LoopSelectorInterface] | None = (
                (decisions, loop_selector)
                if decisions is not None and loop_selector is not None
                else None
            )
    ```
  - `select_for`: replace the `try:` block (`:221-233`, from `        try:` through
    `            raise CapacityDeferred(self._clock.now() + self._backoff, str(exc)) from exc`)
    with:
    ```python
            weighted: WeightedCandidates | None = None
            try:
                # (keep the "The pool, never None" comment of :222-225 here)
                if self._declaration is None:
                    engine_id, _selection = await self._selector.select_engine(
                        job.project_id,
                        inputs.requirement,
                        allow_list=self._pool,
                        affinity_engine=inputs.affinity,
                    )
                else:
                    weighted = await self._selector.weighted_candidates(
                        job.project_id,
                        inputs.requirement,
                        allow_list=self._pool,
                        affinity_engine=inputs.affinity,
                    )
                    engine_id, _selection = await self._selector.select_from(weighted)
            except NoEligibleEngine as exc:
                raise CapacityDeferred(self._clock.now() + self._backoff, str(exc)) from exc
    ```
    and replace the method's last two lines
    (`        await self._jobs.assign_engine(job.id, owner=self._owner, engine_id=engine_id)` and
    `        return adapter`) with:
    ```python
            await self._jobs.assign_engine(job.id, owner=self._owner, engine_id=engine_id)
            if (
                weighted is not None
                and self._declaration is not None
                and adapter.descriptor.tier is EngineTier.PAID
            ):
                decisions, loop_selector = self._declaration
                declaration = PaidFallbackDeclaration(
                    engine_id=engine_id.value,
                    invocation="subprocess",
                    sovereign=loop_selector.sovereign_exclusions(weighted),
                )
                await decisions.append_event(
                    job.project_id,
                    job.cycle,
                    job.id,
                    EventKind.PAID_FALLBACK_DECLARED,
                    declaration.to_payload(),
                )
            return adapter
    ```
    `self._selector` stays typed `EngineSelector` (the concrete class has both new methods).
- `src/vibey/bootstrap.py` (962 lines): add `from vibey.application.loop_selector import LoopSelector`
  (after `from vibey.application.job_dispatcher import JobDispatcher`); in `build_full_worker`,
  replace the unique text
  ```
          local_engines=local.enabled_engines,
          metrics=metrics,
      )
  ```
  with
  ```
          local_engines=local.enabled_engines,
          metrics=metrics,
          decisions=PostgresReviewLedger(resources.ledger, phase=Phase.BUILD),
          loop_selector=LoopSelector(descriptors=BY_ENGINE_ID),
      )
  ```
  (`PostgresReviewLedger`, `Phase` and `BY_ENGINE_ID` are already imported, `:96`, `:80`, `:104`.)
- New test file `tests/application/test_paid_fallback_subprocess.py` (line 1: the provenance
  comment copied from `tests/application/test_engine_selection.py`).
- The registry needs nothing new.

## Acceptance criteria
- [ ] Every test below passes; `tests/application/test_engine_selection.py` passes unedited
      (`git diff --stat HEAD -- tests/application/test_engine_selection.py` is empty).
- [ ] `grep -n "PAID_FALLBACK_DECLARED" src/vibey/application/engine_selection.py` shows one append.
- [ ] The declaration's payload never holds a datetime or a `resets_at`/`credits` key (the
      `PaidFallbackDeclaration` type of lane `loops-ledger-kinds` already proves it; one test
      below checks the concrete event).
- [ ] `src/vibey/application/*` stays at 100% branch coverage.

## Tests to write first (TDD)
`tests/application/test_paid_fallback_subprocess.py`. Seams only: `FakeEngineHealthRepository`
and `FakeRotationCursorRepository` from `tests.fakes.engines`; `FakeJobRepository` and `make_job`
from `tests.fakes.queue`; `InMemoryLedger` and `review_ledger` from `tests.fakes.ledger`
(`ledger = InMemoryLedger()`, `decisions = review_ledger(ledger, phase=Phase.BUILD)`); the real
`EngineHealthService`, `EngineSelector(descriptors=BY_ENGINE_ID)` and
`LoopSelector(descriptors=BY_ENGINE_ID)`; adapters are
`ScriptedEngine(descriptor=BY_ENGINE_ID[e], base_dir=tmp_path / e.value)`. Copy the record helper
of `tests/application/test_engine_selector.py:70-94` as `_record`. The job is
`replace(make_job(project_id, attempts=1), project_id=project_id, state=JobState.LEASED, lease_owner="w1")`,
given to `FakeJobRepository([job])`, with `owner="w1"`. Use `EngineId.SOVEREIGNLOOP`.
- `test_a_paid_selection_declares_why_each_sovereign_adapter_lost`: pool
  `{SOVEREIGNLOOP, CLAUDELOOP}`; the sovereign row has `circuit="open", capacity_state="WindowExhausted"`;
  claudeloop is healthy → `select_for` returns the claudeloop adapter; `ledger.events` holds
  exactly one event with `kind == EventKind.PAID_FALLBACK_DECLARED`, `phase == Phase.BUILD`,
  `job_id == job.id`, and `payload == {"loop_id": "paidloop", "engine_id": "claudeloop", "invocation": "subprocess", "sovereign_adapters": [{"engine_id": "sovereignloop", "reason": "circuit_open", "capacity_state": "WindowExhausted", "detail": ""}], "rule": "sub-doctrine 8.a"}`.
- `test_a_sovereign_selection_writes_nothing`: both rows healthy → the sovereign adapter;
  `ledger.events == ()`.
- `test_a_missing_sovereign_row_is_named`: no sovereign row, healthy claudeloop → one event whose
  `sovereign_adapters == [{"engine_id": "sovereignloop", "reason": "no_health_row", "capacity_state": None, "detail": ""}]`.
- `test_a_paid_only_pool_still_declares`: pool `{CLAUDELOOP}` only → one event with
  `sovereign_adapters == []`.
- `test_the_declaration_follows_the_assignment`: `ledger.fail_next_append(RuntimeError("ledger down"))`,
  the paid case → `select_for` raises `RuntimeError`, and `(await jobs.get(job.id)).assigned_engine == "claudeloop"`.
- `test_without_the_collaborators_nothing_is_declared`: the paid case with neither `decisions`
  nor `loop_selector` → the claudeloop adapter, and a separately held `InMemoryLedger` stays empty.
- `test_half_a_declaration_is_refused`: `decisions` without `loop_selector`, and the reverse,
  each raise `ValueError` with the message of behaviour 1.
- `test_no_eligible_engine_still_defers_on_the_declaring_path`: no rows, both collaborators set
  → `CapacityDeferred` whose `retry_at` is the clock's now plus 5 minutes; `ledger.events == ()`.
- `test_the_event_carries_no_time`: in the first test's event, no value anywhere in the payload
  (walk dicts and lists) is a `datetime`, and no key is `resets_at`, `credits` or `capacity`.

## Checks the lane must run (all must pass)
First run `uv run ruff format src/vibey/application/engine_selection.py src/vibey/bootstrap.py tests/application/test_paid_fallback_subprocess.py`.

    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/application/test_paid_fallback_subprocess.py tests/application/test_engine_selection.py tests/application/test_loop_selector.py tests/application/test_weighted_candidates.py tests/fakes tests/test_bootstrap.py
    uv run pytest -q -p no:cacheprovider tests/system/test_full_worker_faked.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    git diff --stat HEAD -- tests/application/test_engine_selection.py
    git diff --stat

`tests/system/test_full_worker_faked.py` needs PostgreSQL (`VIBEY_TEST_DATABASE_URL`); after lane
`fakes-harness-decouple` it is marked `integration`. It proves `build_full_worker` still composes.

## Out of scope
- Service mode's declaration and `LoopRouted` (lane `loops-selecting-loop-provider`).
- `RotationHandoffService` (wind-down) selections: they are handoffs, not BUILD selections.
- Changing `EngineSelector`, `LoopSelector` or the event types.
- Protected tests: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-loop-selector`, `fakes-ledger`, `orm-ledger`, `engines-pool`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
