## Title
feat(loop-service): a seat host consumes its model's queue exclusively, persists each result and answers the caller
ADR-0046 lane L28a (slug `loops-seat-host-core`).

## Why
Draft ADR-0046 §3 (`/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-two-loops.md:140-191`) runs every model's work through one **seat host**: "Every seat queue is consumed by exactly one seat host with an *exclusive* consumer, so a second instance for the same model is refused at the broker and exits with an 8.c message." Sub-doctrine 8.c (`src/vibey_tools/gh/docs/doctrines.md:196-234`) runs "a single instance per model", and its replay rule says a message delivered twice is answered once. The superseded host (`specs/rmq-r22-loop-service-host.md`; closing note `issue-audit/updates/369.md`) carries its rules into the seat host: a (dead-letter a malformed or foreign message), c (re-send a persisted result, never re-run), e (reject past `start_by`), f (reject an unsafe request) and h (run; persist, then publish, then acknowledge). Rules b, d and g (redelivery of an active run, a non-terminal run directory, the worktree fence) are lane `loops-seat-host-fence`; progress and drain are lane `loops-seat-host-drain`.

The host never reads engine health and never classifies capacity (ADR-0046 §2): an exit code travels back as it is, and the caller classifies it. **Decision D1** of the design sheet: a seat host starts, and is ready, as soon as it holds its exclusive consumer; it never checks the model runtime. A runner whose backend is missing exits 78 (`EXIT_CODE_BACKEND_MISCONFIGURED`, `src/vibey/domain/engine.py:23` at integration `d3b4a388`) on its own, and the host returns that code unchanged. Decision D6: the seat's model always wins in the run's environment. 8.g (`doctrines.md:316-324`): the host records each run (subject RUN) and each rejection (subject REJECT). *Security impact*: the model and the environment come only from the loop's configuration, never from a message.

**Order of the checks.** The superseded R22 checked the persisted result (c) before the executor's safety check (f). This lane checks f first: reading `<cwd>/.vibey/diagnostics/<run_id>.result.json` for a `cwd` the message chose, before `cwd` is known to lie under `[loop_services] root`, would touch the filesystem outside the root (*Security impact*). The only effect is which reason a request that is both unsafe and already answered gets.

## Required behaviour
1. **`class LoopInstanceRefused(VibeyError)`** is appended to `src/vibey/domain/errors.py`:
   ```python
   class LoopInstanceRefused(VibeyError):
       """The broker refused this loop's exclusive consumer: another instance already
       consumes the queue (sub-doctrine 8.c)."""

       def __init__(self, queue: str) -> None:
           self.queue = queue
           super().__init__(
               f"another instance already consumes {queue}: "
               "sub-doctrine 8.c runs a single instance per model"
           )
   ```
2. **`class SeatHost`** in `src/vibey/infrastructure/loop_service/seat_host.py`, exactly as below (it is written in full so that lanes `loops-seat-host-fence` and `loops-seat-host-drain` can anchor their edits on its text; keep every line, comment and name).
   ```python
   @dataclass(slots=True)
   class _ActiveRun:
       """One request this host is running. `delivery` is the one to settle when the run
       ends: a redelivery of the same request replaces it (lane loops-seat-host-fence)."""

       request: RunRequest
       delivery: AmqpDeliveryInterface
       started_at: datetime
       run: LocalRunInterface | None = None


   class SeatHost:
       """Consumes one seat queue exclusively and runs what arrives on it.

       Declared by `interfaces/seat_host_interface.py`.
       """

       def __init__(
           self,
           *,
           loop_id: LoopId,
           seat: str,
           model: str | None,
           amqp: AmqpClientInterface,
           names: RunQueueNamesInterface,
           codec: RunProtocolCodec,
           executor: LocalRunExecutorInterface,
           results: RunResultStoreInterface,
           config: LoopConfigInterface,
           environ: Mapping[str, str],
           clock: Clock,
           instance: str,
           measurements: LoopMeasurementLogInterface,
           prefetch: int,
           logger: Logger | None = None,
       ) -> None:
           if loop_id is LoopId.SOVEREIGNLOOP and model is None:
               raise ValueError("a sovereignloop seat host needs the model its seat carries")
           if prefetch < 1:
               raise ValueError("prefetch must be at least 1")
           self._loop_id = loop_id
           self._seat = seat
           self._model = model
           self._amqp = amqp
           self._names = names
           self._codec = codec
           self._executor = executor
           self._results = results
           self._config = config
           self._environ = environ
           self._clock = clock
           self._instance = instance
           self._measurements = measurements
           self._prefetch = prefetch
           self._log: Logger = logger if logger is not None else structlog.get_logger(__name__)
           # Validates the slug: an invalid or reserved seat name fails here, at construction.
           self._queue = names.seat_queue(loop_id, seat)
           self._tag: str | None = None
           self._active: dict[UUID, _ActiveRun] = {}

       @property
       def loop_id(self) -> LoopId:
           return self._loop_id

       @property
       def seat(self) -> str:
           return self._seat

       @property
       def model(self) -> str | None:
           return self._model

       @property
       def consuming(self) -> bool:
           return self._tag is not None

       async def declare(self) -> None:
           key = self._names.seat_key(self._loop_id, self._seat)
           await self._amqp.declare_exchange(self._names.runs_exchange(), "direct")
           await self._amqp.declare_exchange(self._names.dead_exchange(), "direct")
           await self._amqp.declare_queue(
               self._queue,
               arguments=self._names.queue_arguments(
                   dead_key=key,
                   delivery_limit=self._config.delivery_limit,
                   consumer_timeout_seconds=self._config.consumer_timeout_seconds,
               ),
           )
           await self._amqp.bind(self._queue, self._names.runs_exchange(), key)
           dead = self._names.seat_dead_queue(self._loop_id, self._seat)
           await self._amqp.declare_queue(dead, arguments={"x-queue-type": "quorum"})
           await self._amqp.bind(dead, self._names.dead_exchange(), key)

       async def consume(self) -> None:
           if self._tag is not None:
               return
           try:
               self._tag = await self._amqp.consume(
                   self._queue, prefetch=self._prefetch, handler=self.handle, exclusive=True
               )
           except AmqpExclusiveConsumerRefused as exc:
               raise LoopInstanceRefused(self._queue) from exc
           self._log.info(
               "seat_consuming",
               loop=self._loop_id.value,
               seat=self._seat,
               model=self._model,
               prefetch=self._prefetch,
               instance=self._instance,
           )

       async def cancel(self) -> None:
           tag, self._tag = self._tag, None
           if tag is not None:
               await self._amqp.cancel(tag)
               self._log.info("seat_cancelled", loop=self._loop_id.value, seat=self._seat)

       async def start(self) -> None:
           await self.declare()
           await self.consume()

       async def handle(self, delivery: AmqpDeliveryInterface) -> None:
           """The consumer callback for one delivery of the seat queue. Public so a test
           can hand it a second delivery while a first is still running, which the
           in-memory broker (one push at a time per queue) cannot do."""
           try:
               message = self._codec.from_bytes(delivery.body)
           except MalformedRunMessage as exc:
               await self._dead_letter(delivery, f"malformed: {exc}")
               return
           if not isinstance(message, RunRequest) or message.loop_id != self._loop_id:
               await self._dead_letter(delivery, f"not a {self._loop_id.value} run request")
               return
           request = message
           reason = self._executor.reason_to_reject(request)
           if reason is not None:
               await self._reject(delivery, request, reason)
               return
           stored = self._results.read(request.cwd, request.run_id)
           if stored is not None:
               await self._reply(delivery, request.run_id, stored)
               await delivery.complete()
               self._log.info("seat_result_republished", seat=self._seat, run_id=str(request.run_id))
               return
           if self._clock.now() > request.start_by:
               await self._reject(delivery, request, "not started before start_by")
               return
           await self._run(delivery, request)

       async def _run(self, delivery: AmqpDeliveryInterface, request: RunRequest) -> None:
           try:
               overlay = self._environment_for(request.engine_id)
           except ConfigError as exc:
               await self._reject(delivery, request, f"loop environment is misconfigured: {exc}")
               return
           started_at = self._clock.now()
           entry = _ActiveRun(request=request, delivery=delivery, started_at=started_at)
           self._active[request.run_id] = entry
           try:
               try:
                   run = await self._executor.start(request, env_overlay=overlay)
               except OSError as exc:
                   await self._reject(
                       entry.delivery, request, f"could not start {request.engine_id}: {exc}"
                   )
                   return
               entry.run = run
               queued = max(0.0, (started_at - request.requested_at).total_seconds())
               await self._reply(
                   entry.delivery,
                   request.run_id,
                   RunAccepted(
                       run_id=request.run_id,
                       loop_id=self._loop_id,
                       engine_id=request.engine_id,
                       seat=self._seat,
                       model=self._model,
                       instance=self._instance,
                       pid=run.pid,
                       started_at=started_at,
                       queued_seconds=queued,
                   ),
               )
               self._log.info(
                   "seat_run_started",
                   seat=self._seat,
                   run_id=str(request.run_id),
                   engine=request.engine_id,
                   pid=run.pid,
               )
               exit_code = await run.wait(float(request.deadline_seconds))
               if exit_code is None:
                   await run.stop(float(self._config.supersede_grace_seconds))
                   status = RunStatus.DEADLINE_EXCEEDED
                   detail = f"run exceeded its deadline of {request.deadline_seconds}s"
               else:
                   status = RunStatus.EXITED
                   detail = ""
               stdout, stderr = run.output()
               finished_at = self._clock.now()
               result = RunResult(
                   run_id=request.run_id,
                   status=status,
                   exit_code=exit_code,
                   meta_status=run.meta_status(),
                   started_at=started_at,
                   finished_at=finished_at,
                   detail=detail,
                   stdout=stdout,
                   stderr=stderr,
                   cached_at=None,
               )
               await self._finish(entry.delivery, request, result)
               self._measurements.record(
                   LoopMeasurement(
                       loop_id=self._loop_id,
                       subject=MeasurementSubject.RUN,
                       at=finished_at,
                       seat=self._seat,
                       engine_id=request.engine_id,
                       model=self._model,
                       latency_ms=(finished_at - started_at).total_seconds() * 1000,
                       waited_seconds=queued,
                       outcome=f"{status.value}:{exit_code}",
                   )
               )
           finally:
               self._active.pop(request.run_id, None)

       async def _reject(
           self, delivery: AmqpDeliveryInterface, request: RunRequest, detail: str
       ) -> None:
           finished_at = self._clock.now()
           result = RunResult(
               run_id=request.run_id,
               status=RunStatus.REJECTED,
               exit_code=None,
               meta_status=None,
               started_at=None,
               finished_at=finished_at,
               detail=detail,
               stdout=None,
               stderr=None,
               cached_at=None,
           )
           # Never persisted: the caller may retry the same run id later.
           await self._reply(delivery, request.run_id, result)
           await delivery.complete()
           self._measurements.record(
               LoopMeasurement(
                   loop_id=self._loop_id,
                   subject=MeasurementSubject.REJECT,
                   at=finished_at,
                   seat=self._seat,
                   engine_id=request.engine_id,
                   model=self._model,
                   outcome=detail,
               )
           )
           self._log.info("seat_run_rejected", seat=self._seat, run_id=str(request.run_id), detail=detail)

       async def _finish(
           self, delivery: AmqpDeliveryInterface, request: RunRequest, result: RunResult
       ) -> None:
           # Persist, then publish, then acknowledge: a crash at any point leaves a
           # redelivery that re-sends the persisted result, or one that runs again.
           if request.purpose is RunPurpose.RUN:
               self._results.write(request.cwd, result)
           await self._reply(delivery, request.run_id, result)
           await delivery.complete()
           self._log.info(
               "seat_run_finished",
               seat=self._seat,
               run_id=str(request.run_id),
               status=result.status.value,
               exit_code=result.exit_code,
           )

       async def _reply(
           self, delivery: AmqpDeliveryInterface, run_id: UUID, message: RunMessage
       ) -> None:
           reply_to = delivery.properties.reply_to
           if reply_to is None:
               return
           # The default exchange routes to the queue named `reply_to`. Not mandatory: a
           # caller that has gone away must not keep the run from being acknowledged.
           await self._amqp.publish(
               "",
               reply_to,
               self._codec.to_bytes(message),
               AmqpProperties(correlation_id=str(run_id), type=type(message).__name__),
               mandatory=False,
           )

       async def _dead_letter(self, delivery: AmqpDeliveryInterface, reason: str) -> None:
           await delivery.dead_letter()
           self._log.warning(
               "seat_request_dead_lettered", loop=self._loop_id.value, seat=self._seat, reason=reason
           )

       def _environment_for(self, engine_id: str) -> dict[str, str]:
           """What this run gets on top of the loop's own environment. Only the loop's
           configuration sets it, never a message (ADR-0046, Security impact)."""
           if self._loop_id is not LoopId.SOVEREIGNLOOP or self._model is None:
               return {}
           engine = ENGINE_ID_PARSER.known(engine_id)
           overlay = (
               {}
               if engine is None
               else LocalEndpointEnvironment(self._environ, model=self._model).overlay_for(engine)
           )
           if engine is EngineId.SOVEREIGNLOOP:
               # The seat's model always wins over an inherited SOVEREIGNLOOP_MODEL (D6).
               overlay[SOVEREIGNLOOP_MODEL_ENV] = self._model
           return overlay
   ```
   Module docstring (above the imports): the seat host of ADR-0046 §3; one exclusive consumer per model (8.c); persist, publish, acknowledge; never reads health or classifies capacity (§2); never checks the model runtime (D1: a missing backend is the runner's exit 78, returned unchanged). `__all__ = ["SeatHost"]`.
3. Behaviour that follows from the code, each covered by a test below:
   - a message that is not valid JSON, not a `RunRequest`, or for the other loop is dead-lettered (it lands in the seat's dead queue) and nothing is started;
   - an unsafe request is answered `REJECTED` with the executor's reason; a request past `start_by` with `"not started before start_by"`; a run whose environment cannot be built with `"loop environment is misconfigured: <ConfigError>"`; a spawn failure with `"could not start <engine>: <error>"`. A rejection is never persisted, and records one REJECT measurement whose `outcome` is the detail;
   - a request whose result is persisted is answered with that result and acknowledged, and nothing starts;
   - a run replies `RunAccepted` (with `queued_seconds = started_at − requested_at`, never negative), then a `RunResult`: `EXITED` with the exit code and `meta_status`, or `DEADLINE_EXCEEDED` with `exit_code=None` after `stop(supersede_grace_seconds)`. A `RUN` result is persisted before it is published, and the delivery is acknowledged last; a `PROBE` result is not persisted;
   - every reply goes to the default exchange `""` with routing key `reply_to` and `correlation_id = str(run_id)`, not mandatory; a request without `reply_to` is still run and persisted;
   - a second host for the same seat raises `LoopInstanceRefused`, whose message ends "sub-doctrine 8.c runs a single instance per model".
4. **Interface** `src/vibey/infrastructure/loop_service/interfaces/seat_host_interface.py`: `@runtime_checkable class SeatHostInterface(Protocol)` with the properties `loop_id -> LoopId`, `seat -> str`, `model -> str | None`, `consuming -> bool`, and `async declare(self) -> None`, `async consume(self) -> None` ("raises LoopInstanceRefused when another instance consumes the seat"), `async cancel(self) -> None`, `async start(self) -> None`, each with a one-line docstring.
5. **In-memory fake**, appended to `tests/fakes/loops.py`:
   ```python
   class FakeSeatHost:
       """SeatHostInterface in memory: records its calls; `refuse=True` makes consume raise
       LoopInstanceRefused, as the broker does for a second instance of a model."""

       def __init__(
           self,
           *,
           loop_id: LoopId = LoopId.SOVEREIGNLOOP,
           seat: str = "gpt-oss-20b",
           model: str | None = "gpt-oss:20b",
           refuse: bool = False,
       ) -> None:
           self._loop_id = loop_id
           self._seat = seat
           self._model = model
           self.refuse = refuse
           self._consuming = False
           self.calls: list[str] = []

       @property
       def loop_id(self) -> LoopId:
           return self._loop_id

       @property
       def seat(self) -> str:
           return self._seat

       @property
       def model(self) -> str | None:
           return self._model

       @property
       def consuming(self) -> bool:
           return self._consuming

       async def declare(self) -> None:
           self.calls.append("declare")

       async def consume(self) -> None:
           self.calls.append("consume")
           if self.refuse:
               raise LoopInstanceRefused(f"vibey.runs.{self._loop_id.value}.{self._seat}")
           self._consuming = True

       async def cancel(self) -> None:
           self.calls.append("cancel")
           self._consuming = False

       async def start(self) -> None:
           await self.declare()
           await self.consume()
   ```
6. **Registry**: `SeatHostInterface` is appended to `DRIVER_SEAMS`; `REGISTRY` gains `FakeRegistration(port=SeatHostInterface, build=FakeSeatHost)`.

## Where to change
Line 1 of every new file is the provenance comment, copied byte for byte from line 1 of `src/vibey/infrastructure/process/reaper.py`.
- **Preconditions** (stop and report `blocked: <what>` if one fails; do not work around it):
  - `grep -n "the default exchange cannot be declared" src/vibey_tools/bootstrap/vibey_bootstrap/amqp/memory.py` prints a line: the in-memory broker routes the default exchange `""` (lane `surfaces-amqp-publish-modes`, ADR-0047 S07). Every reply of this lane is a publish to `""`.
  - `grep -n "class AmqpExclusiveConsumerRefused" src/vibey_tools/bootstrap/vibey_bootstrap/amqp/errors.py` and `grep -n "def queue_depth" src/vibey_tools/bootstrap/vibey_bootstrap/amqp/memory.py` print a line each (lanes `loops-amqp-exclusive-consume`, `loops-amqp-queue-depth`).
  - `grep -n "SOVEREIGNLOOP_MODEL_ENV" src/vibey/infrastructure/engines/local_engines.py` prints a line (lane `loops-vibey-local-engine-names`).
  - `uv run python -c "from vibey.domain.loop_services_config import LoopConfig; LoopConfig()"` succeeds: every `LoopConfig` field has its default (lane `loops-config-loop-services`).
- `src/vibey/domain/errors.py` (about 87 lines): append the class of behaviour 1 at the end of the file.
- **New** `src/vibey/infrastructure/loop_service/seat_host.py` (behaviour 2). Imports:
  `from collections.abc import Mapping`, `from dataclasses import dataclass`, `from datetime import datetime`, `from uuid import UUID`, `structlog`, `from vibey_bootstrap.amqp import AmqpProperties`, `from vibey_bootstrap.amqp.errors import AmqpExclusiveConsumerRefused`, `from vibey_bootstrap.amqp.interfaces import AmqpClientInterface, AmqpDeliveryInterface`, `from vibey.application.interfaces import Clock, Logger`, `from vibey.domain.config import ConfigError`, `from vibey.domain.engine import ENGINE_ID_PARSER, EngineId`, `from vibey.domain.errors import LoopInstanceRefused, MalformedRunMessage`, `from vibey.domain.interfaces.loop_services_config_interface import LoopConfigInterface`, `from vibey.domain.interfaces.run_protocol_interface import RunQueueNamesInterface`, `from vibey.domain.loop import LoopId`, `from vibey.domain.loop_events import LoopMeasurement, MeasurementSubject`, `from vibey.domain.run_codec import RunProtocolCodec`, `from vibey.domain.run_protocol import RunAccepted, RunMessage, RunPurpose, RunRequest, RunResult, RunStatus`, `from vibey.infrastructure.engines.local_engines import SOVEREIGNLOOP_MODEL_ENV, LocalEndpointEnvironment`, `from vibey.infrastructure.loop_service.interfaces.local_run_executor_interface import LocalRunExecutorInterface, LocalRunInterface`, `from vibey.infrastructure.loop_service.interfaces.measurement_log_interface import LoopMeasurementLogInterface`, `from vibey.infrastructure.loop_service.interfaces.result_store_interface import RunResultStoreInterface`.
- **New** `src/vibey/infrastructure/loop_service/interfaces/seat_host_interface.py` (behaviour 4), in the style of `src/vibey/infrastructure/process/interfaces/reaper_interface.py`.
- **`tests/fakes/loops.py`**: add `from vibey.domain.errors import LoopInstanceRefused` and `from vibey.domain.loop import LoopId` to its import block with `edit_file` (skip any already there); append the class of behaviour 5 at the end with `edit_file`.
- **`tests/fakes/registry.py`**: run the registration script of lane `loops-result-store` (the `register_fakes.py` block) with only these lists, then delete the script:
  ```python
  IMPORTS = [
      "from tests.fakes.loops import FakeSeatHost",
      "from vibey.infrastructure.loop_service.interfaces.seat_host_interface import SeatHostInterface",
  ]
  SEAMS = ["SeatHostInterface"]
  ENTRIES = ["FakeRegistration(port=SeatHostInterface, build=FakeSeatHost)"]
  ```
- Then `uv run ruff check --fix` and `uv run ruff format` on `src/vibey/domain/errors.py src/vibey/infrastructure/loop_service tests/fakes/loops.py tests/fakes/registry.py tests/infrastructure/loop_service`. Formatting may re-wrap lines of behaviour 2; that is fine.
- **New** `tests/infrastructure/loop_service/test_seat_host_core.py`.

## Acceptance criteria
- [ ] Every bullet of behaviour 3 has a test.
- [ ] A run's result is written before it is published, and its delivery is acknowledged only after both: a failing write leaves the delivery unacknowledged and publishes no `RunResult`.
- [ ] The host starts with only the broker: it takes no model runtime (D1), and a runner's exit 78 comes back as `EXITED` with `exit_code == 78`.
- [ ] The tests need no broker, no Ollama and no network: `InMemoryAmqpClient` and the loop fakes only. No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`; `tests/meta/patching_baseline.json` does not change; `tests/fakes/test_port_parity.py` passes.
- [ ] `tests/domain/test_domain_purity.py` passes; 100% branch coverage of `src/vibey/domain/*` and `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_seat_host_core.py`. Helpers (the fence and drain lanes append their tests to new files and build their own rigs the same way):
```python
NOW = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)
SEAT = "gpt-oss-20b"
MODEL = "gpt-oss:20b"
REPLIES = "caller.replies"


class _Clock:
    """A Clock (application/interfaces/system.py) the test sets by hand."""

    def __init__(self, instant: datetime) -> None:
        self.instant = instant

    def now(self) -> datetime:
        return self.instant


@dataclass
class _Rig:
    amqp: InMemoryAmqpClient
    host: SeatHost
    executor: FakeLocalRunExecutor
    results: InMemoryRunResultStore
    measurements: InMemoryLoopMeasurementLog
    clock: _Clock
    names: RunQueueNames
    codec: RunProtocolCodec


async def _rig(
    *,
    executor: FakeLocalRunExecutor | None = None,
    results: InMemoryRunResultStore | None = None,
    loop_id: LoopId = LoopId.SOVEREIGNLOOP,
    seat: str = SEAT,
    model: str | None = MODEL,
    environ: Mapping[str, str] | None = None,
) -> _Rig:
    amqp = InMemoryAmqpClient()
    await amqp.connect()
    await amqp.declare_queue(REPLIES)
    names, codec, clock = RunQueueNames(), RunProtocolCodec(), _Clock(NOW)
    executor = executor or FakeLocalRunExecutor()
    results = results or InMemoryRunResultStore()
    measurements = InMemoryLoopMeasurementLog()
    host = SeatHost(
        loop_id=loop_id, seat=seat, model=model, amqp=amqp, names=names, codec=codec,
        executor=executor, results=results, config=LoopConfig(), environ=environ or {},
        clock=clock, instance="host-1", measurements=measurements, prefetch=1,
    )
    await host.start()
    return _Rig(amqp, host, executor, results, measurements, clock, names, codec)


def _request(tmp_path: Path, **overrides: object) -> RunRequest:
    cwd = tmp_path / "wt"
    cwd.mkdir(exist_ok=True)
    fields: dict[str, object] = dict(
        run_id=uuid4(), loop_id=LoopId.SOVEREIGNLOOP, engine_id="sovereignloop", route_id=None,
        model_pin=None, purpose=RunPurpose.RUN, args=("run", "plan.md"), cwd=str(cwd),
        run_dir=None, supersedes=None, deadline_seconds=60, start_by=NOW + timedelta(minutes=5),
        capture_output=False, requested_at=NOW - timedelta(seconds=3), caller="test",
    )
    fields.update(overrides)
    return RunRequest(**fields)


async def _send(rig: _Rig, body: bytes, *, reply_to: str | None = REPLIES) -> None:
    await rig.amqp.publish(
        rig.names.runs_exchange(),
        rig.names.seat_key(rig.host.loop_id, rig.host.seat),
        body,
        AmqpProperties(message_id=str(uuid4()), reply_to=reply_to),
    )


async def _replies(rig: _Rig) -> list[object]:
    messages: list[object] = []
    while (delivery := await rig.amqp.get(REPLIES)) is not None:
        messages.append(rig.codec.from_bytes(delivery.body))
        await delivery.complete()
    return messages
```
The in-memory broker runs the host's handler inside `publish`, so `await _send(...)` returns after the request was handled. `LoopConfig()` has the defaults of lane `loops-config-loop-services` (`delivery_limit` 3, `consumer_timeout_seconds` 21600, `supersede_grace_seconds` 30). Tests:
- `test_declare_creates_the_seat_queue_and_its_dead_queue`: re-declaring `names.seat_queue(SOVEREIGNLOOP, SEAT)` with `names.queue_arguments(dead_key=names.seat_key(SOVEREIGNLOOP, SEAT), delivery_limit=3, consumer_timeout_seconds=21600)` returns its name (equal arguments), and re-declaring `names.seat_dead_queue(SOVEREIGNLOOP, SEAT)` with `{"x-queue-type": "quorum"}` does too; `rig.host.consuming is True`.
- `test_a_second_host_for_the_same_seat_is_refused_citing_8c`: a second `SeatHost` for the same seat on the same broker: `await second.start()` raises `LoopInstanceRefused` whose `queue` is the seat queue and whose message ends "sub-doctrine 8.c runs a single instance per model"; `second.consuming is False`.
- `test_runs_a_request_and_replies_accepted_then_result`: `FakeLocalRunExecutor(meta_status="finished")`; after `_send(rig, codec.to_bytes(request))`: replies are `[RunAccepted, RunResult]`; the accepted has `seat == SEAT`, `model == MODEL`, `instance == "host-1"`, `pid == 4242`, `queued_seconds == 3.0`; the result is `EXITED`, `exit_code == 0`, `meta_status == "finished"`; `rig.results.read(request.cwd, request.run_id) == result`; `await rig.amqp.get(seat_queue)` is `None`; the last measurement is subject `RUN`, `outcome == "exited:0"`, `waited_seconds == 3.0`.
- `test_a_failed_write_publishes_no_result_and_leaves_the_delivery_unacked`: `InMemoryRunResultStore(fail_with=OSError("disk full"))`; `_send` raises `OSError`; the only reply is `RunAccepted`; after `await rig.amqp.close()` and `await rig.amqp.connect()`, `await rig.amqp.get(seat_queue)` returns the request with `delivery_count == 1` (it was never acknowledged).
- `test_malformed_or_foreign_messages_are_dead_lettered`: `b"not json"`, `codec.to_bytes(<a RunResult>)` and a `RunRequest` with `loop_id=LoopId.PAIDLOOP`, each sent in turn, each lands in `names.seat_dead_queue(SOVEREIGNLOOP, SEAT)`; `rig.executor.starts == []`; no reply.
- `test_a_persisted_result_is_republished_not_rerun`: `results.write(request.cwd, stored)` beforehand; the one reply equals `stored`; `rig.executor.starts == []`; the seat queue is empty.
- `test_an_unsafe_request_is_rejected_with_the_executors_reason`: `FakeLocalRunExecutor(reject="cwd /etc is outside the loop root /work")` → one `RunResult` `REJECTED` with that detail; nothing persisted; the last measurement is `REJECT` with that outcome.
- `test_a_late_request_is_rejected`: `start_by=NOW - timedelta(seconds=1)` → `REJECTED`, detail `"not started before start_by"`, nothing started.
- `test_a_spawn_failure_rejects_the_run`: `FakeLocalRunExecutor(start_error=FileNotFoundError(2, "No such file or directory", "sovereignloop"))` → `REJECTED` whose detail starts `"could not start sovereignloop: "`; no `RunAccepted`.
- `test_the_deadline_stops_the_run`: `FakeLocalRunExecutor(hang=True)`, `deadline_seconds=1` → result `DEADLINE_EXCEEDED`, `exit_code is None`, detail `"run exceeded its deadline of 1s"`; `rig.executor.runs[0].stops == [30.0]`; the measurement outcome is `"deadline_exceeded:None"`.
- `test_the_host_needs_no_model_runtime_and_returns_exit_78_unchanged` (D1): `FakeLocalRunExecutor(exit_code=EXIT_CODE_BACKEND_MISCONFIGURED)` → `EXITED`, `exit_code == 78`, outcome `"exited:78"`.
- `test_the_seat_model_always_wins_in_the_run_environment` (D6): `environ={"VIBEY_OLLAMA_URL": "http://ollama:11434", "SOVEREIGNLOOP_MODEL": "other"}` → `rig.executor.starts[0][1] == {"SOVEREIGNLOOP_BASE_URL": "http://ollama:11434/v1", "SOVEREIGNLOOP_MODEL": MODEL}`.
- `test_other_adapters_get_no_model_key_and_paid_seats_no_overlay`: a sovereign request with `engine_id="opencode"` starts with overlay `{}`; a paidloop host (`loop_id=PAIDLOOP, seat="claudeloop", model=None`) given a paid request with `engine_id="claudeloop"` starts with overlay `{}` even with `VIBEY_OLLAMA_URL` set.
- `test_a_misconfigured_endpoint_rejects_the_run`: `environ={"VIBEY_OLLAMA_URL": "ftp://nope"}` → `REJECTED` whose detail starts `"loop environment is misconfigured: "`; nothing started.
- `test_a_probe_is_run_but_not_persisted`: `purpose=RunPurpose.PROBE, args=("--version",), capture_output=True`, `FakeLocalRunExecutor(stdout="sovereignloop 3.0.0")` → the result carries `stdout == "sovereignloop 3.0.0"`; `rig.results.writes == []`.
- `test_a_request_without_reply_to_still_runs_and_persists`: `_send(..., reply_to=None)` → no reply, one start, the result persisted, the seat queue empty.
- `test_a_sovereign_host_needs_a_model_and_a_positive_prefetch`: `SeatHost(..., model=None)` for sovereignloop raises `ValueError`; `prefetch=0` raises `ValueError`; seat `"probe"` raises the `ValueError` of `RunQueueNames`.
- `test_cancel_stops_consuming_and_consume_resumes`: after `cancel()`, `consuming is False` and a sent request stays in the seat queue (`queue_depth == 1`); `consume()` runs it; a second `consume()` does nothing; a second `cancel()` does nothing.
- `test_the_host_and_its_fake_satisfy_the_interface`: `isinstance(rig.host, SeatHostInterface)`, `isinstance(FakeSeatHost(), SeatHostInterface)`; `FakeSeatHost(refuse=True).start()` raises `LoopInstanceRefused` after recording `["declare", "consume"]`.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/domain/test_domain_purity.py tests/fakes tests/meta/test_patching_ratchet.py tests/application/test_interfaces_convention.py
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/domain/*' --fail-under=100
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
git status --short
```
Nothing here is OS-specific (8.h: Arch Linux and macOS alike).

## Out of scope
- Rules b, d and g and the worktree fence (lane `loops-seat-host-fence`); progress, `busy`, control, supersede-by-broadcast and the drain (lane `loops-seat-host-drain`); residency switching (lane `loops-resident-schedule`).
- Logging `seat_runtime_unreachable` and the startup line (D1; lanes `loops-service-process`, `loops-cli-loop-service`).
- The dead-letter replier and the control consumer (lane `loops-control-and-dead-letters`): they must declare the seat's dead queue with the same arguments, `{"x-queue-type": "quorum"}`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Protected tests are never edited.
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject. Follow `STORM/EDITING-RULES.md`.

**Depends on:** `loops-local-run-executor`, `loops-amqp-exclusive-consume`, `loops-config-loop-services`, `loops-vibey-local-engine-names`
- `loops-local-run-executor`: the executor seam and `FakeLocalRunExecutor`; with it, the result store and measurement log and their fakes.
- `loops-amqp-exclusive-consume`: `consume(..., exclusive=True)` and `AmqpExclusiveConsumerRefused` in `vibey_bootstrap.amqp`.
- `loops-config-loop-services`: `LoopConfig` and `LoopConfigInterface`.
- `loops-vibey-local-engine-names`: `SOVEREIGNLOOP_MODEL_ENV` and the renamed overlay.
- Not named by the design sheet, and flagged to the coordinator: `surfaces-amqp-publish-modes` (the default exchange `""` in `vibey_bootstrap.amqp`), checked by the first precondition above.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
