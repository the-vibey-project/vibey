## Title
feat(rotation): SelectingLoopProvider routes a BUILD job through its loop's queue and records LoopRouted and any paid fallback

ADR-0046 lane L16 (slug `loops-selecting-loop-provider`).

## Why
Draft ADR-0046 §3, "Flow for a BUILD job" (`specs/ADR-two-loops.md:169-179`):
"1. `select_for` makes the outer decision. 2. It publishes a route request to `<loop>` and
awaits `RunRouted`, bounded by `route_wait_seconds`. 3. It records the selection, assigns the
routed engine to the job, and writes `LoopRouted`. 4. It returns an adapter bound to that
engine." §5 (`:226-236`): `UNROUTABLE` makes "the outer layer decide again with that loop
excluded, for this selection only"; queue saturation "never triggers a paid fallback".
§2 (`:125-127`): paidloop's choice writes `PaidFallbackDeclared` "in both invocation modes".
§10 (`:303`) names `application/loop_provider.py (SelectingLoopProvider)`. Sub-doctrines 8.a
(`src/vibey_tools/gh/docs/doctrines.md:99-112`), 8.c (`:196`), 8.g (`:316`: always measured) and
7.c (`:82`) are the rules; design-sheet decisions D7 (route replies), D9 (route measurements
travel in `RunRouted` and the caller writes them into `LoopRouted`) and D10 (decision events go
through `PhaseLedger` with `Phase.BUILD`) apply.

At integration `d3b4a388` the only BUILD provider is `SelectingEngineProvider`
(`src/vibey/application/engine_selection.py:167-248`), which picks the engine in process. This
lane adds the service-mode provider beside it. Composition picks it only in service mode (lane
`loops-invocation-composition`); nothing observable changes by default.

## Required behaviour
1. `SelectingLoopProvider` implements `EngineProvider`
   (`src/vibey/application/interfaces/engines.py:27-41`): a `pool` property (the adapters'
   engine ids narrowed by `allow_list`, exactly as `engine_selection.py:192`) and
   `async select_for(job) -> EngineAdapter`.
2. `select_for`:
   1. `inputs = selection_inputs_for_job(job, pool=self._pool)` (reused from
      `engine_selection.py:80-164`, 10.e) and the local-engine preflight loop copied from
      `engine_selection.py:208-220`;
   2. `weighted = await selector.weighted_candidates(job.project_id, inputs.requirement, allow_list=self._pool, affinity_engine=inputs.affinity)`;
   3. with `excluded: dict[LoopId, str] = {}`, repeat:
      - `decision = loop_selector.choose(weighted, excluded=excluded)`; `None` → raise
        `CapacityDeferred(clock.now() + backoff, <detail of behaviour 3>)`;
      - route `RouteRequest(route_id=route_ids(), loop_id=decision.loop_id, project_id=job.project_id, candidates=tuple(RouteCandidate(c.engine_id.value, c.effective_weight) for c in decision.candidates), pin=None, model_pin=None, min_context=None, requested_at=clock.now(), caller=owner)`
        with `routed = await routing.route(request, wait=route_wait)`;
      - `routed is None` → raise `EngineQueueSaturated(clock.now() + route_wait, f"no {loop} router answered within {route_wait.total_seconds():g}s")`
        (for 30 s: `no sovereignloop router answered within 30s`);
      - `routed.status is RouteStatus.DEAD_LETTERED` → raise
        `EngineQueueSaturated(clock.now() + route_wait, f"the {loop} router dead-lettered the route: {routed.reason}")`;
      - `routed.status is RouteStatus.UNROUTABLE` → `excluded[decision.loop_id] = routed.reason`,
        and try again (the next `choose` skips that loop; with both loops excluded it returns None);
      - `RouteStatus.ROUTED` → accept (behaviour 4).
   Saturation and dead letters never reach paidloop; only UNROUTABLE moves the job on.
3. The `CapacityDeferred` detail is `"no loop can take this job: " + "; ".join(reasons)`, where
   `reasons` is, in order, `f"{e.engine_id}: {e.reason.value}"` plus `f" ({e.detail})"` when
   `e.detail` is non-empty, for every `e` in `weighted.exclusions`, then
   `f"{loop}: unroutable ({reason})"` for every excluded loop; when `reasons` is empty the text
   after the colon is `no adapter in the pool has positive weight`. Nothing is routed when the
   first `choose` returns None.
4. Accepting a ROUTED reply:
   - `routed.engine_id` must be the value of an engine in `pool`; otherwise raise
     `CapacityDeferred(clock.now() + backoff, f"routed engine {routed.engine_id} has no configured adapter")`;
   - `await health.record_selection(job.project_id, engine_id)`; when `metrics` is set,
     `metrics.record_engine_selection(job.project_id, engine_id)` inside `suppress(Exception)`
     (as `engine_selection.py:244-246`); `await jobs.assign_engine(job.id, owner=owner, engine_id=engine_id)`;
   - append `EventKind.LOOP_ROUTED` with
     `LoopRoutedRecord(route_id=routed.route_id, loop_id=decision.loop_id, engine_id=engine_id.value, seat=routed.seat or "", model=routed.model, switched=routed.switched, reason=routed.reason, route_ms=routed.route_ms, seat_depth=routed.seat_depth, seat_oldest_wait_seconds=routed.seat_oldest_wait_seconds).to_payload()`
     (the route's measurements, 8.g, D9);
   - when `decision.loop_id is LoopId.PAIDLOOP`, then append `EventKind.PAID_FALLBACK_DECLARED`
     with `PaidFallbackDeclaration(engine_id=engine_id.value, invocation="service", sovereign=decision.sovereign_exclusions).to_payload()`;
   - both through `decisions.append_event(job.project_id, job.cycle, job.id, kind, payload)`;
   - return `binder.bind(routed, job=job)`.
5. No capacity state is read from the loop, and none is sent: `RouteRequest` carries only engine
   ids and weights (the codec of lane `loops-run-codec` refuses anything else).

## Where to change
Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` first.
- New `src/vibey/application/loop_provider.py` (line 1: the provenance comment copied from
  `src/vibey/application/engine_selection.py`):
  ```python
  """The service-mode BUILD engine provider (ADR-0046 §2-§3): both rotation layers on the bus.

  ``select_for`` makes the outer decision (``LoopSelector``: sovereignloop first), publishes a
  ``RouteRequest`` to the chosen loop and awaits its ``RunRouted``; the loop runs its own inner
  round robin and residency and answers with the adapter, seat and model. The provider records
  the selection, assigns the routed engine, writes ``LoopRouted`` -- and ``PaidFallbackDeclared``
  when the loop is paidloop -- and returns an adapter bound to the routed engine before
  ``start`` (§3, steps 1-4).

  - UNROUTABLE is a routing fact, not a capacity state: the outer layer decides again with that
    loop excluded, for this selection only (§5).
  - No answer within ``route_wait``, or a dead-lettered route, is queue saturation: the job
    defers with ``capacity=False`` and is never handed to paid (busy is not "cannot carry", 8.a).
  - The loop never reads health, and no capacity state crosses the wire (§2).
  """

  from collections.abc import Callable, Mapping
  from contextlib import suppress
  from datetime import timedelta
  from uuid import UUID, uuid4

  from vibey.application.dto import JobRecord, LoopDecision, WeightedCandidates
  from vibey.application.engine_selection import selection_inputs_for_job
  from vibey.application.interfaces import (
      Clock,
      EngineAdapter,
      EngineHealthServiceInterface,
      EngineSelectorInterface,
      LoopRoutingPort,
      LoopSelectorInterface,
      PhaseLedger,
      RoutedAdapterBinderInterface,
      TelemetryMetrics,
  )
  from vibey.application.ports import JobRepository
  from vibey.application.worker import CapacityDeferred, EngineQueueSaturated
  from vibey.domain.engine import EngineId
  from vibey.domain.ledger import EventKind
  from vibey.domain.loop import LoopId
  from vibey.domain.loop_events import LoopRoutedRecord, PaidFallbackDeclaration
  from vibey.domain.run_protocol import RouteCandidate, RouteRequest, RouteStatus, RunRouted


  class SelectingLoopProvider:
      """The service-mode ``EngineProvider`` (``application/interfaces/engines.py``)."""

      def __init__(
          self,
          *,
          selector: EngineSelectorInterface,
          loop_selector: LoopSelectorInterface,
          routing: LoopRoutingPort,
          binder: RoutedAdapterBinderInterface,
          health: EngineHealthServiceInterface,
          adapters: Mapping[EngineId, EngineAdapter],
          jobs: JobRepository,
          decisions: PhaseLedger,
          clock: Clock,
          owner: str,
          allow_list: frozenset[EngineId] | None = None,
          backoff: timedelta = timedelta(minutes=5),
          route_wait: timedelta = timedelta(seconds=30),
          local_engines: tuple[EngineId, ...] = (),
          metrics: TelemetryMetrics | None = None,
          route_ids: Callable[[], UUID] = uuid4,
      ) -> None:
          self._selector = selector
          self._loop_selector = loop_selector
          self._routing = routing
          self._binder = binder
          self._health = health
          self._adapters = adapters
          self._jobs = jobs
          self._decisions = decisions
          self._clock = clock
          self._owner = owner
          self._backoff = backoff
          self._route_wait = route_wait
          self._metrics = metrics
          self._route_ids = route_ids
          self._pool = frozenset(adapters) if allow_list is None else frozenset(adapters) & allow_list
          self._local_engines = tuple(engine for engine in local_engines if engine in self._pool)
          self._pooled = {engine_id.value: engine_id for engine_id in self._pool}

      @property
      def pool(self) -> frozenset[EngineId]:
          return self._pool

      async def select_for(self, job: JobRecord) -> EngineAdapter:
          ...  # behaviour 2, written out in full

      def _request(self, job: JobRecord, decision: LoopDecision) -> RouteRequest:
          ...  # the RouteRequest of behaviour 2

      async def _accept(
          self, job: JobRecord, decision: LoopDecision, routed: RunRouted
      ) -> EngineAdapter:
          ...  # behaviour 4

      @staticmethod
      def _nothing_can_take(weighted: WeightedCandidates, excluded: Mapping[LoopId, str]) -> str:
          ...  # behaviour 3


  __all__ = ["SelectingLoopProvider"]
  ```
  Write every `...` out; the loop of behaviour 2 is a `while True:` whose only exits are the
  `return` and the three `raise`s (each UNROUTABLE adds a new key to `excluded`, and `choose`
  never returns an excluded loop, so it ends within three turns).
- No other source file changes. The registry needs nothing new: the tests use the fakes of lane
  `loops-routing-ports`, and `SelectingLoopProvider` is checked against `EngineProvider`.
- New test file `tests/application/test_loop_provider.py`.

## Acceptance criteria
- [ ] Every test below passes.
- [ ] `isinstance(provider, EngineProvider)`.
- [ ] `grep -n "capacity" src/vibey/application/loop_provider.py` shows only `CapacityDeferred`
      and docstring text: the provider reads no capacity state from a reply.
- [ ] `src/vibey/application/*` stays at 100% branch coverage; mypy strict and lint-imports pass.

## Tests to write first (TDD)
`tests/application/test_loop_provider.py` (line 1: the provenance comment). Seams only:
`FakeLoopRouting` and `FakeRoutedAdapterBinder` (`tests.fakes.loops`); `FakeEngineHealthRepository`
and `FakeRotationCursorRepository` (`tests.fakes.engines`); `FakeJobRepository` and `make_job`
(`tests.fakes.queue`); `InMemoryLedger` and `review_ledger` (`tests.fakes.ledger`,
`decisions = review_ledger(ledger, phase=Phase.BUILD)`); the real `EngineHealthService`,
`EngineSelector(descriptors=BY_ENGINE_ID)` and `LoopSelector(descriptors=BY_ENGINE_ID)`; adapters
`ScriptedEngine(descriptor=BY_ENGINE_ID[e], base_dir=tmp_path / e.value)`, the binder built with
the same objects keyed by `e.value`. `NOW = datetime(2026, 9, 22, 12, tzinfo=UTC)`, a
`FixedClock` returning it, `route_ids=lambda: ROUTE_ID` with a fixed UUID, `owner="w1"`, and the
job `replace(make_job(project_id, attempts=1), project_id=project_id, state=JobState.LEASED, lease_owner="w1")`
in `FakeJobRepository([job])`. Health rows come from a copy of `_healthy_record`
(`tests/application/test_engine_selector.py:70-94`). A reply helper builds
`RunRouted(route_id=uuid4(), loop_id=..., status=..., engine_id=..., seat=..., model=..., switched=False, reason=..., routed_at=NOW, route_ms=2.5, seat_depth=0, seat_oldest_wait_seconds=None)`.
Use `EngineId.SOVEREIGNLOOP`.
- `test_a_healthy_sovereign_pool_routes_to_sovereignloop_and_records_the_route`: healthy
  sovereign and claudeloop rows; replies `{SOVEREIGNLOOP: ROUTED sovereignloop, seat "gpt-oss-20b", model "gpt-oss:20b", reason "resident"}`
  → returns the sovereign adapter; `routing.requests == [RouteRequest(route_id=ROUTE_ID, loop_id=LoopId.SOVEREIGNLOOP, project_id=project_id, candidates=(RouteCandidate("sovereignloop", 1),), pin=None, model_pin=None, min_context=None, requested_at=NOW, caller="w1")]`;
  `routing.waits == [timedelta(seconds=30)]`; the job's `assigned_engine == "sovereignloop"`;
  `(await health.get_or_create(project_id, EngineId.SOVEREIGNLOOP)).selected_count == 1`;
  `ledger.events` is exactly one `LoopRouted` event, `phase == Phase.BUILD`, whose payload equals
  `LoopRoutedRecord(route_id=ROUTE_ID, loop_id=LoopId.SOVEREIGNLOOP, engine_id="sovereignloop", seat="gpt-oss-20b", model="gpt-oss:20b", switched=False, reason="resident", route_ms=2.5, seat_depth=0, seat_oldest_wait_seconds=None).to_payload()`.
- `test_an_unroutable_sovereign_loop_falls_to_a_declared_paid_adapter`: replies
  `{SOVEREIGNLOOP: UNROUTABLE reason "no local model can carry this job", PAIDLOOP: ROUTED claudeloop seat "claudeloop"}`
  → the claudeloop adapter; two requests (sovereignloop, then paidloop with
  `candidates == (RouteCandidate("claudeloop", 1),)`); events `[LoopRouted, PaidFallbackDeclared]`
  in that order; the second payload equals
  `PaidFallbackDeclaration(engine_id="claudeloop", invocation="service", sovereign=(AdapterExclusion("sovereignloop", ExclusionReason.UNROUTABLE, detail="no local model can carry this job"),)).to_payload()`.
- `test_an_unhealthy_sovereign_pool_goes_straight_to_paidloop`: the sovereign row has
  `circuit="open", capacity_state="WindowExhausted"` → one request, to paidloop; the declaration
  names `circuit_open` with `capacity_state "WindowExhausted"`.
- `test_no_router_answer_is_saturation_never_a_fallback`: replies `{}` with both rows healthy →
  raises `EngineQueueSaturated` with `retry_at == NOW + timedelta(seconds=30)` and
  `detail == "no sovereignloop router answered within 30s"`; exactly one request (never paidloop);
  `ledger.events == ()`; the job's `assigned_engine is None`.
- `test_a_dead_lettered_route_is_saturation`: sovereign reply `DEAD_LETTERED`, reason
  `"route request dead-lettered after 3 deliveries"` → `EngineQueueSaturated` whose detail is
  `"the sovereignloop router dead-lettered the route: route request dead-lettered after 3 deliveries"`;
  one request.
- `test_both_loops_unroutable_defers_with_every_reason`: both replies UNROUTABLE (reasons
  `"a"`, `"b"`) → `CapacityDeferred` with `retry_at == NOW + timedelta(minutes=5)` and
  `detail == "no loop can take this job: sovereignloop: unroutable (a); paidloop: unroutable (b)"`.
- `test_nothing_eligible_defers_without_routing`: no rows, pool `{CLAUDELOOP}` →
  `CapacityDeferred` whose detail is `"no loop can take this job: claudeloop: no_health_row"`;
  `routing.requests == []`.
- `test_an_exclusion_detail_is_quoted_in_the_deferral`: a claudeloop row with `circuit="tripped"`
  as the only pool engine → the detail ends with `"claudeloop: circuit_open (unrecognized circuit state tripped)"`.
- `test_a_pool_whose_candidates_all_weigh_zero_says_so`: one claudeloop row with
  `ewma_failure=1.0` → `detail == "no loop can take this job: no adapter in the pool has positive weight"`.
- `test_a_routed_engine_outside_the_pool_defers`: paidloop replies ROUTED `codexloop` while the
  pool is `{CLAUDELOOP}` (sovereign row open) → `CapacityDeferred` with
  `detail == "routed engine codexloop has no configured adapter"`; `ledger.events == ()`.
- `test_local_engines_are_preflighted_before_selection`: no sovereign row seeded,
  `local_engines=(EngineId.SOVEREIGNLOOP,)`, the sovereign `ScriptedEngine` installed with
  `auth_ok=True` → the route goes to sovereignloop (the preflight made it eligible).
- `test_a_warm_paid_session_never_beats_a_healthy_sovereign_adapter`: job `attempts=2`,
  `assigned_engine="claudeloop"` (affinity), both rows healthy → the only request is to sovereignloop.
- `test_metrics_record_the_routed_selection`: with `metrics=TelemetryMetrics()`
  (`vibey.infrastructure.otel`) → `metrics.export_metrics(project_id)["engine_selections"] == {"sovereignloop": 1}`.
- `test_the_pool_is_the_adapters_narrowed_by_the_allow_list` and
  `test_the_provider_is_an_engine_provider`.

## Checks the lane must run (all must pass)
First run `uv run ruff format src/vibey/application/loop_provider.py tests/application/test_loop_provider.py`.

    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/application/test_loop_provider.py tests/application/test_loop_selector.py tests/application/test_paid_fallback_subprocess.py tests/application/test_engine_selection.py tests/application/test_interfaces_convention.py tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    git diff --stat

## Out of scope
- Composing it in `build_full_worker` (lane `loops-invocation-composition`), the real
  `LoopClient` (lane `loops-client`) and `RoutedAdapterBinder` (lane `loops-service-adapter-run`).
- Pinned runs (DESIGN, DECOMPOSE, `vibey loop submit`): they send one run message, not a route.
- `SelectingEngineProvider` and the subprocess declaration (lane `loops-subprocess-fallback-declared`).
- Protected tests: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-routing-ports`, `loops-queue-saturated`, `loops-subprocess-fallback-declared`, `orm-job-settle`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
