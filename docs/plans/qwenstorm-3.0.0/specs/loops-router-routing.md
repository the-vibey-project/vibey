## Title
feat(loop-service): each loop's router consumes its intake exclusively and routes each job to a seat, once
ADR-0046 lane L30a (slug `loops-router-routing`).

## Why
Draft ADR-0046 §3 (`STORM/specs/ADR-two-loops.md:140-191`) gives each loop one **router**: it declares the loop's topology (the table at lines 144–152), consumes its intake queue `vibey.runs.<loop>` **exclusively** ("so one router per loop is not a second instance of any model", and "the exclusive intake consumer stops a rogue second instance from draining a loop's queue", *Security impact*), and answers each `vibey.run.route/1` with a `vibey.run.routed/1`. The inner layer runs here (§2, lines 129–136): SWRR over the candidates the caller sends, with the loop's own cursors, and for sovereignloop the residency choice first (§4, lines 195–200: resident, then default, then first declared that can carry the job, else `UNROUTABLE` with "no local model can carry this job"). The idempotency table (lines 183–191): "`RouteStore` creates the record once. A redelivered route re-sends the stored `RunRouted` and never advances SWRR twice." The loop never reads engine health and never classifies capacity (§2). Sub-doctrine 8.c (`src/vibey_tools/gh/docs/doctrines.md:196-234`: both layers run on the bus, with dead-letter queues and idempotency) and 8.g (`:316-324`: every route is measured, subject ROUTE, with the seat's depth and oldest wait). The pure parts exist (`SeatChooser`, `ResidencyPolicy`, lanes `loops-seat-chooser`, `loops-residency-policy`); so do the stores (lane `loops-state-stores`) and the backlog (lane `loops-resident-schedule`).

Forwarding run requests is lane `loops-router-forwarding`; answering dead letters and probes is lanes `loops-control-and-dead-letters` and `loops-probe-consumer` (decision D5: all three run in the router's process).

## Required behaviour
1. **`class LoopRouter`** in `src/vibey/infrastructure/loop_service/router.py`, built with keyword arguments:
   `LoopRouter(*, loop_id: LoopId, amqp: AmqpClientInterface, names: RunQueueNamesInterface, codec: RunProtocolCodec, config: LoopConfigInterface, seats: Mapping[str, str], adapters: frozenset[str], default_adapter: str, routes: RouteStoreInterface, cursors: LoopCursorStoreInterface, chooser: SeatChooserInterface, residency: ResidencyPolicyInterface, declarations: tuple[ModelDeclaration, ...], default_model: str | None, resident_model: Callable[[], str | None], backlog: SeatBacklogInterface, measurements: LoopMeasurementLogInterface, clock: Clock, logger: Logger | None = None)`.
   `seats` maps each declared seat slug to its declared name (a model for sovereignloop, an engine id for paidloop); `adapters` is the set of engine ids the loop can run. It raises `ValueError(f"the default adapter {default_adapter} is not an adapter of {loop_id.value}")` when `default_adapter not in adapters`. It keeps `self._intake = names.intake_queue(loop_id)` and `self._tag: str | None = None`.
2. **`async start(self) -> None`** declares, then consumes:
   ```python
   names, loop = self._names, self._loop_id
   await self._amqp.declare_exchange(names.runs_exchange(), "direct")
   await self._amqp.declare_exchange(names.dead_exchange(), "direct")
   await self._amqp.declare_exchange(names.control_exchange(), "topic")
   await self._declare_pair(self._intake, names.intake_dead_queue(loop), names.intake_key(loop))
   for seat in self._seats:
       await self._declare_pair(
           names.seat_queue(loop, seat), names.seat_dead_queue(loop, seat), names.seat_key(loop, seat)
       )
   await self._amqp.declare_queue(names.probe_queue(loop))
   await self._amqp.bind(names.probe_queue(loop), names.runs_exchange(), names.probe_key(loop))
   try:
       self._tag = await self._amqp.consume(
           self._intake, prefetch=self._config.router_prefetch, handler=self.handle, exclusive=True
       )
   except AmqpExclusiveConsumerRefused as exc:
       raise LoopInstanceRefused(self._intake) from exc
   self._log.info("router_started", loop=loop.value, seats=list(self._seats), prefetch=self._config.router_prefetch)
   ```
   with
   ```python
   async def _declare_pair(self, queue: str, dead: str, key: str) -> None:
       await self._amqp.declare_queue(
           queue,
           arguments=self._names.queue_arguments(
               dead_key=key,
               delivery_limit=self._config.delivery_limit,
               consumer_timeout_seconds=self._config.consumer_timeout_seconds,
           ),
       )
       await self._amqp.bind(queue, self._names.runs_exchange(), key)
       await self._amqp.declare_queue(dead, arguments={"x-queue-type": "quorum"})
       await self._amqp.bind(dead, self._names.dead_exchange(), key)
   ```
   The seat queues and their dead queues are declared with exactly the arguments `SeatHost.declare` uses (lane `loops-seat-host-core`), so either may declare first. The probe queue is a classic queue: no arguments.
3. **`async stop(self) -> None`**: cancels the intake consumer when there is one (`tag, self._tag = self._tag, None`), logging `router_stopped`; a second call does nothing.
4. **`async route(self, request: RouteRequest) -> RunRouted`**:
   ```python
   began = time.monotonic()
   now = self._clock.now()
   asked = [candidate.engine_id for candidate in request.candidates]
   if request.pin is not None:
       asked.append(request.pin)
   outside = [engine for engine in asked if engine not in self._adapters]
   if outside:
       return await self._settle(
           request, None, reason=f"engine {outside[0]} is not an adapter of {self._loop_id.value}",
           model=None, switched=False, began=began, now=now,
       )
   model: str | None = None
   switched = False
   reason = ""
   if self._loop_id is LoopId.SOVEREIGNLOOP:
       residency = self._residency.choose(
           resident=self._resident_model(),
           default=self._default_model,
           declared=self._declarations,
           model_pin=request.model_pin,
           min_context=request.min_context,
       )
       if residency is None:
           return await self._settle(
               request, None, reason=UNROUTABLE_NO_MODEL, model=None, switched=False, began=began, now=now
           )
       model, switched, reason = residency.model, residency.switched, residency.reason
       candidates = request.candidates
   else:
       # A paid seat is its adapter: the round robin is offered only adapters with a declared seat.
       candidates = tuple(c for c in request.candidates if c.engine_id in self._seats)
   decision = self._chooser.choose(
       loop_id=self._loop_id,
       candidates=candidates,
       cursors=self._cursors.load(request.project_id),
       model=model,
       pin=request.pin,
       default_adapter=self._default_adapter,
   )
   if decision.choice is None:
       return await self._settle(
           request, None, reason=decision.reason, model=None, switched=False, began=began, now=now
       )
   if decision.choice.seat not in self._seats:
       return await self._settle(
           request, None, reason=f"seat {decision.choice.seat} is not declared by {self._loop_id.value}",
           model=None, switched=False, began=began, now=now,
       )
   return await self._settle(
       request, decision.choice, reason=reason or decision.reason, model=model,
       switched=switched, began=began, now=now,
   )
   ```
   The model is the loop's own decision: a `model_pin` is honoured only when it names a declared model (`ResidencyPolicy` never chooses an undeclared one; *Security impact*).
5. **`_settle`** builds, stores, measures and returns the route:
   ```python
   async def _settle(
       self, request: RouteRequest, choice: SeatChoice | None, *, reason: str,
       model: str | None, switched: bool, began: float, now: datetime,
   ) -> RunRouted:
       depth: int | None = None
       oldest: float | None = None
       if choice is not None:
           depth = await self._amqp.queue_depth(self._names.seat_queue(self._loop_id, choice.seat))
           self._backlog.trim(choice.seat, depth or 0)
           oldest = self._backlog.oldest_wait_seconds(choice.seat, now)
       routed = RunRouted(
           route_id=request.route_id,
           loop_id=self._loop_id,
           status=RouteStatus.UNROUTABLE if choice is None else RouteStatus.ROUTED,
           engine_id=None if choice is None else choice.engine_id,
           seat=None if choice is None else choice.seat,
           model=None if choice is None else model,
           switched=choice is not None and switched,
           reason=reason,
           routed_at=now,
           route_ms=(time.monotonic() - began) * 1000,
           seat_depth=depth,
           seat_oldest_wait_seconds=oldest,
       )
       stored = self._routes.create_once(routed)
       if choice is not None and stored == routed:
           # After the route is stored, never before: a redelivered route never advances
           # the round robin twice, and a crash in between only misses one advance.
           self._cursors.save(request.project_id, choice.cursors)
       self._measurements.record(
           LoopMeasurement(
               loop_id=self._loop_id,
               subject=MeasurementSubject.ROUTE,
               at=now,
               seat=stored.seat,
               engine_id=stored.engine_id,
               model=stored.model,
               latency_ms=stored.route_ms,
               queue_depth=stored.seat_depth,
               waited_seconds=stored.seat_oldest_wait_seconds,
               outcome=stored.status.value,
           )
       )
       return stored
   ```
   An unroutable route is stored too, so a redelivery gets the same answer.
6. **`async handle(self, delivery: AmqpDeliveryInterface) -> None`** — the intake consumer callback (public, so a test can hand it a delivery directly; the in-memory broker pushes one delivery at a time per queue):
   ```python
   try:
       message = self._codec.from_bytes(delivery.body)
   except MalformedRunMessage as exc:
       await self._dead_letter(delivery, f"malformed: {exc}")
       return
   if isinstance(message, RouteRequest) and message.loop_id == self._loop_id:
       await self._answer_route(delivery, message)
       return
   await self._dead_letter(delivery, f"not a {self._loop_id.value} route or run request")
   ```
   with
   ```python
   async def _answer_route(self, delivery: AmqpDeliveryInterface, request: RouteRequest) -> None:
       stored = self._routes.get(request.route_id)
       if stored is None:
           stored = await self.route(request)
       else:
           self._log.info("route_resent", loop=self._loop_id.value, route_id=str(request.route_id))
       await self._reply(delivery, str(request.route_id), stored)
       await delivery.complete()

   async def _reply(self, delivery: AmqpDeliveryInterface, correlation_id: str, message: RunMessage) -> None:
       reply_to = delivery.properties.reply_to
       if reply_to is None:
           return
       await self._amqp.publish(
           "",
           reply_to,
           self._codec.to_bytes(message),
           AmqpProperties(correlation_id=correlation_id, type=type(message).__name__),
           mandatory=False,
       )

   async def _dead_letter(self, delivery: AmqpDeliveryInterface, reason: str) -> None:
       await delivery.dead_letter()
       self._log.warning("router_message_dead_lettered", loop=self._loop_id.value, reason=reason)
   ```
   (Lane `loops-router-forwarding` inserts the `RunRequest` branch before the final dead-letter line.)
7. **Interface** `src/vibey/infrastructure/loop_service/interfaces/router_interface.py`: `@runtime_checkable class LoopRouterInterface(Protocol)` with `async start(self) -> None` ("raises LoopInstanceRefused when another router consumes the intake"), `async stop(self) -> None`, `async route(self, request: RouteRequest) -> RunRouted`.
8. **Fake**, appended to `tests/fakes/loops.py`:
   ```python
   class FakeLoopRouter:
       """LoopRouterInterface in memory: routes every request to the scripted engine and
       seat, or answers UNROUTABLE when none is scripted."""

       def __init__(
           self,
           *,
           engine_id: str | None = None,
           seat: str | None = None,
           model: str | None = None,
           reason: str = "",
       ) -> None:
           self.engine_id = engine_id
           self.seat = seat
           self.model = model
           self.reason = reason
           self.requests: list[RouteRequest] = []
           self.started = False
           self.stopped = False

       async def start(self) -> None:
           self.started = True

       async def stop(self) -> None:
           self.stopped = True

       async def route(self, request: RouteRequest) -> RunRouted:
           self.requests.append(request)
           routed = self.engine_id is not None and self.seat is not None
           return RunRouted(
               route_id=request.route_id,
               loop_id=request.loop_id,
               status=RouteStatus.ROUTED if routed else RouteStatus.UNROUTABLE,
               engine_id=self.engine_id if routed else None,
               seat=self.seat if routed else None,
               model=self.model if routed else None,
               switched=False,
               reason=self.reason or ("" if routed else "FakeLoopRouter has no scripted route"),
               routed_at=request.requested_at,
               route_ms=0.0,
               seat_depth=None,
               seat_oldest_wait_seconds=None,
           )
   ```
9. **Registry**: `LoopRouterInterface` is appended to `DRIVER_SEAMS`; `REGISTRY` gains `FakeRegistration(port=LoopRouterInterface, build=FakeLoopRouter)`.

## Where to change
Line 1 of every new file is the provenance comment, copied byte for byte from line 1 of `src/vibey/infrastructure/process/reaper.py`.
- **Precondition.** `grep -n "the default exchange cannot be declared" src/vibey_tools/bootstrap/vibey_bootstrap/amqp/memory.py` prints a line (lane `surfaces-amqp-publish-modes`: replies go to the default exchange `""`); if not, stop and report `blocked: the default exchange is not in vibey_bootstrap.amqp`.
- **New** `src/vibey/infrastructure/loop_service/router.py` (behaviours 1–6). Imports: `time`, `from collections.abc import Callable, Mapping`, `from datetime import datetime`, `structlog`, `from vibey_bootstrap.amqp import AmqpProperties`, `from vibey_bootstrap.amqp.errors import AmqpExclusiveConsumerRefused`, `from vibey_bootstrap.amqp.interfaces import AmqpClientInterface, AmqpDeliveryInterface`, `from vibey.application.interfaces import Clock, Logger`, `from vibey.domain.errors import LoopInstanceRefused, MalformedRunMessage`, `from vibey.domain.interfaces.loop_services_config_interface import LoopConfigInterface`, `from vibey.domain.interfaces.residency_interface import ResidencyPolicyInterface`, `from vibey.domain.interfaces.run_protocol_interface import RunQueueNamesInterface`, `from vibey.domain.interfaces.seat_choice_interface import SeatChooserInterface`, `from vibey.domain.loop import LoopId`, `from vibey.domain.loop_events import LoopMeasurement, MeasurementSubject`, `from vibey.domain.residency import UNROUTABLE_NO_MODEL, ModelDeclaration`, `from vibey.domain.run_codec import RunProtocolCodec`, `from vibey.domain.run_protocol import RouteRequest, RouteStatus, RunMessage, RunRouted`, `from vibey.domain.seat_choice import SeatChoice`, `from vibey.infrastructure.loop_service.interfaces.measurement_log_interface import LoopMeasurementLogInterface`, `from vibey.infrastructure.loop_service.interfaces.resident_schedule_interface import SeatBacklogInterface`, `from vibey.infrastructure.loop_service.interfaces.route_store_interface import LoopCursorStoreInterface, RouteStoreInterface`. `__all__ = ["LoopRouter"]`. Module docstring: ADR-0046 §3's router; exclusive intake (8.c, *Security impact*); routes once (the idempotency table); database-free; never reads health or classifies capacity (§2). `time.monotonic()` measures only `route_ms`; every decision reads the injected clock.
- **New** `src/vibey/infrastructure/loop_service/interfaces/router_interface.py` (behaviour 7).
- **`tests/fakes/loops.py`**: add `RouteRequest`, `RouteStatus` (and `RunRouted` if missing) to its `vibey.domain.run_protocol` import with `edit_file`; append the class of behaviour 8 at the end with `edit_file`.
- **`tests/fakes/registry.py`**: run the registration script of lane `loops-result-store` (the `register_fakes.py` block) with only these lists, then delete the script:
  ```python
  IMPORTS = [
      "from tests.fakes.loops import FakeLoopRouter",
      "from vibey.infrastructure.loop_service.interfaces.router_interface import LoopRouterInterface",
  ]
  SEAMS = ["LoopRouterInterface"]
  ENTRIES = ["FakeRegistration(port=LoopRouterInterface, build=FakeLoopRouter)"]
  ```
- Then `uv run ruff check --fix` and `uv run ruff format` on `src/vibey/infrastructure/loop_service tests/fakes/loops.py tests/fakes/registry.py tests/infrastructure/loop_service`.
- **New** `tests/infrastructure/loop_service/test_router_routing.py`.

## Acceptance criteria
- [ ] A second router on the same loop is refused (`LoopInstanceRefused`, citing 8.c).
- [ ] A route id is routed once: a repeated or redelivered route request gets the stored route and advances no cursor.
- [ ] Sovereignloop routes to the resident model's seat when it can carry the job, and answers `UNROUTABLE` with `"no local model can carry this job"` when no declared model can.
- [ ] Paidloop's round robin alternates between equally weighted adapters, `claudeloop` first, and never routes to an undeclared seat.
- [ ] Every route records one ROUTE measurement with the seat's depth and oldest wait.
- [ ] No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`; `tests/meta/patching_baseline.json` does not change; `tests/fakes/test_port_parity.py` passes.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_router_routing.py`. Constants: `NOW = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)`, `REPLIES = "caller.replies"`, `PROJECT = uuid4()`, `SOVEREIGN_SEATS = {"gpt-oss-20b": "gpt-oss:20b", "qwen3-coder-30b": "qwen3-coder:30b"}`, `DECLARATIONS = (ModelDeclaration(name="gpt-oss:20b", context_window=131072), ModelDeclaration(name="qwen3-coder:30b", context_window=32768))`, `PAID_SEATS = {"claudeloop": "claudeloop", "codexloop": "codexloop"}`. A local `_Clock` (the four-line class of `test_seat_host_core.py`). A `_Rig` dataclass with `amqp`, `router`, `routes: InMemoryRouteStore`, `cursors: InMemoryLoopCursorStore`, `backlog: SeatBacklog`, `measurements: InMemoryLoopMeasurementLog`, `names`, `codec` and `resident: list[str | None]` (a one-item box the router's `resident_model` reads: `resident_model=lambda: rig_resident[0]`). `async def _rig(loop_id=LoopId.SOVEREIGNLOOP, *, seats=None, resident="gpt-oss:20b") -> _Rig` connects an `InMemoryAmqpClient`, declares `REPLIES`, builds the router with the sovereign values (adapters `frozenset({"sovereignloop", "opencode"})`, default adapter `"sovereignloop"`, `DECLARATIONS`, default model `"gpt-oss:20b"`) or the paid values (adapters `frozenset({"claudeloop", "codexloop", "cursorloop"})`, default adapter `"claudeloop"`, no declarations, default model `None`), `config=LoopConfig()`, `chooser=SeatChooser()`, `residency=ResidencyPolicy()`, and calls `await router.start()`. A helper `_route_request(loop_id=LoopId.SOVEREIGNLOOP, *, candidates=(("sovereignloop", 1),), pin=None, model_pin=None, min_context=None, route_id=None) -> RouteRequest` (`project_id=PROJECT`, `requested_at=NOW`, `caller="test"`). A helper `_send(rig, body, *, reply_to=REPLIES)` publishes to `names.runs_exchange()` with `names.intake_key(loop)`.
- `test_start_declares_the_topology_and_consumes_the_intake_exclusively`: re-declaring the intake queue with `names.queue_arguments(dead_key=names.intake_key(loop), delivery_limit=3, consumer_timeout_seconds=21600)`, each seat queue with its own dead key, each dead queue with `{"x-queue-type": "quorum"}` and the probe queue with no arguments all return their names; `declare_exchange(names.control_exchange(), "direct")` raises `AmqpError` whose text starts `PRECONDITION_FAILED`; a second `LoopRouter` for the same loop on the same broker: `await second.start()` raises `LoopInstanceRefused` whose message ends "sub-doctrine 8.c runs a single instance per model".
- `test_stop_cancels_the_intake_consumer`: after `await rig.router.stop()` a sent route request stays in the intake (`await rig.amqp.queue_depth(names.intake_queue(loop)) == 1`); a second `stop()` does nothing.
- `test_a_candidate_outside_the_loop_is_unroutable`: sovereign, `candidates=(("claudeloop", 1),)` → `UNROUTABLE`, reason `"engine claudeloop is not an adapter of sovereignloop"`; it is stored; `rig.cursors.saves == []`; the ROUTE measurement's outcome is `"unroutable"`.
- `test_sovereign_routes_to_the_resident_models_seat`: → `ROUTED`, `engine_id == "sovereignloop"`, `seat == "gpt-oss-20b"`, `model == "gpt-oss:20b"`, `switched is False`, `reason == "resident"`; `rig.cursors.saves` has one entry for `PROJECT`.
- `test_a_model_pin_switches_to_its_declared_seat`: `model_pin="qwen3-coder:30b"` → seat `"qwen3-coder-30b"`, `switched is True`.
- `test_no_model_that_can_carry_the_job_is_unroutable`: `min_context=200000` → `UNROUTABLE`, `reason == UNROUTABLE_NO_MODEL`.
- `test_paid_rotation_alternates_and_advances_the_cursor_once_per_route`: paid rig, candidates `(("claudeloop", 1), ("codexloop", 1))`, two route requests with different ids → `claudeloop`, then `codexloop`; `len(rig.cursors.saves) == 2`.
- `test_a_repeated_route_id_neither_reroutes_nor_advances`: the same `RouteRequest` routed twice with `await rig.router.route(req)` → equal results; `rig.routes.created == [req.route_id]`; `len(rig.cursors.saves) == 1`.
- `test_a_paid_candidate_without_a_declared_seat_is_skipped`: paid rig with `seats={"claudeloop": "claudeloop"}`, candidates `(("codexloop", 1), ("claudeloop", 1))`, two routes → both `claudeloop`.
- `test_a_pinned_adapter_without_a_declared_seat_is_unroutable`: paid rig, `candidates=()`, `pin="cursorloop"` → `UNROUTABLE`, reason `"seat cursorloop is not declared by paidloop"`.
- `test_no_positive_weight_is_unroutable_with_the_choosers_reason`: paid rig, candidates `(("claudeloop", 0),)` → `UNROUTABLE`, `reason == "no adapter of paidloop has positive weight"`.
- `test_a_route_request_on_the_intake_is_answered_and_acknowledged`: `_send(rig, codec.to_bytes(req))`; the one reply decodes to `rig.routes.get(req.route_id)`, its delivery's `properties.correlation_id == str(req.route_id)`; the intake is empty (`queue_depth == 0`).
- `test_a_redelivered_route_request_resends_the_stored_route`: send the same body twice → two equal replies; `len(rig.cursors.saves) == 1`; one `route_resent` log line (`structlog.testing.capture_logs()`).
- `test_anything_else_on_the_intake_is_dead_lettered`: `b"not json"`, `codec.to_bytes(<a RunResult>)` and a route request for `LoopId.PAIDLOOP` each land in `names.intake_dead_queue(SOVEREIGNLOOP)`; no reply. (Never use a `RunRequest` here: lane `loops-router-forwarding` gives it a branch.)
- `test_a_route_is_measured_with_its_seats_depth_and_oldest_wait`: publish two messages into seat `gpt-oss-20b` (runs exchange, `names.seat_key(...)`; nothing consumes them); `backlog.forwarded("gpt-oss-20b", r1, NOW - timedelta(seconds=10))` and `(..., r2, NOW - timedelta(seconds=5))`; the route has `seat_depth == 2` and `seat_oldest_wait_seconds == 10.0`, and the ROUTE measurement has `queue_depth == 2`, `waited_seconds == 10.0`, `outcome == "routed"`, `latency_ms >= 0`.
- `test_the_default_adapter_must_be_an_adapter`: `LoopRouter(..., default_adapter="claudeloop")` on the sovereign values raises `ValueError`.
- `test_the_router_and_its_fake_satisfy_the_interface`: `isinstance(rig.router, LoopRouterInterface)`, `isinstance(FakeLoopRouter(), LoopRouterInterface)`; `FakeLoopRouter()` answers `UNROUTABLE`; `FakeLoopRouter(engine_id="sovereignloop", seat="gpt-oss-20b", model="gpt-oss:20b")` answers `ROUTED` with those values and records the request; `start`/`stop` set their flags.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/fakes tests/meta/test_patching_ratchet.py tests/application/test_interfaces_convention.py
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
git status --short
```
Nothing here is OS-specific (8.h: Arch Linux and macOS alike).

## Out of scope
- Forwarding run requests and probes (lane `loops-router-forwarding`); dead-letter answers and control (lane `loops-control-and-dead-letters`); probes (lane `loops-probe-consumer`); pruning old routes (the process lane).
- The caller's side (`SelectingLoopProvider`, the loop client: lanes `loops-selecting-loop-provider`, `loops-client`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Protected tests are never edited.
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject. Follow `STORM/EDITING-RULES.md`.

**Depends on:** `loops-state-stores`, `loops-resident-schedule`, `loops-amqp-exclusive-consume`, `loops-config-loop-services`
- `loops-state-stores`: `RouteStore`/`LoopCursorStore` seams and their fakes; with them, `SeatChooser` and `SeatCursor`.
- `loops-resident-schedule`: `SeatBacklog` and `SeatBacklogInterface` (with `trim`); through it the seat host and `LoopInstanceRefused`.
- `loops-amqp-exclusive-consume`: exclusive consume and `queue_depth` in `vibey_bootstrap.amqp`.
- `loops-config-loop-services`: `LoopConfig`, `LoopConfigInterface`.
- Also needed, not named by the design sheet: `surfaces-amqp-publish-modes` (the default exchange), checked by the precondition; it is already required by `loops-seat-host-core`, upstream of this lane.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
