## Title
feat(loop-service): sovereignloop keeps one model resident and switches only between runs, within the starvation bound
ADR-0046 lane L29 (slug `loops-resident-schedule`).

## Why
Draft ADR-0046 §4 (`/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-two-loops.md:193-222`): "Execution consumes only the resident seat … `ResidencySchedule` decides a switch, and only between runs"; "On a switch the loop cancels its consumer on the old seat. If `unload_on_switch` is set (the default), it unloads the old model through the runtime: Ollama `keep_alive: 0`. It then consumes the new seat … vibey never has two models loaded at once"; and "Backlog. The depth of each seat comes from a passive queue declare … The age of a seat's oldest request comes from the router's in-memory first-seen times. After a restart, age is counted from the restart." *Context* (lines 60–69) is why: a 24 GB machine holds one 13–16 GB model at a time, and switching per job would thrash. Sub-doctrine 8.c (`src/vibey_tools/gh/docs/doctrines.md:196-234`): the inner rotation is "mindful that a machine keeps one model resident". 8.g (`:316-324`): every switch is measured (subject SWITCH, latency = the unload, outcome `<from>-><to>`).

Decision D6 of the design sheet: residency switching runs only in `vibey loop-service --role all`, where one process hosts several sovereign seats; in `--role seat` each host consumes its own seat. Decision D1: with no answering runtime, the schedule starts on the default seat and never fails. The pure policy (`ResidencySchedule.next_seat`, lane `loops-residency-schedule`) and the runtime seam (lane `loops-model-runtime`) exist; this lane puts them together with the seat hosts (lane `loops-seat-host-drain`: `busy`, `cancel`, `consume`, the run-finished callback). D14 puts `SeatBacklog` in this module.

## Required behaviour
All in `src/vibey/infrastructure/loop_service/resident_schedule.py`.
1. **`class SeatBacklog`** — in memory by design (after a restart, age counts from the restart):
   ```python
   class SeatBacklog:
       """When the loop first saw each request waiting on each seat (ADR-0046 §4, "Backlog").

       Declared by `interfaces/resident_schedule_interface.py`.
       """

       def __init__(self) -> None:
           self._seen: dict[str, dict[UUID, datetime]] = {}

       def forwarded(self, seat: str, run_id: UUID, at: datetime) -> None:
           # setdefault twice: a redelivered forward keeps the first time the loop saw it.
           self._seen.setdefault(seat, {}).setdefault(run_id, at)

       def started(self, seat: str, run_id: UUID) -> None:
           self._seen.get(seat, {}).pop(run_id, None)

       def trim(self, seat: str, depth: int) -> None:
           """Forget the oldest entries beyond `depth`, the number still waiting in the seat's
           FIFO queue: the ones taken off it have started (a seat host in another process
           cannot report its starts)."""
           waiting = self._seen.get(seat, {})
           for run_id in list(waiting)[: max(0, len(waiting) - depth)]:
               del waiting[run_id]

       def oldest_wait_seconds(self, seat: str, now: datetime) -> float | None:
           waiting = self._seen.get(seat, {})
           if not waiting:
               return None
           return max(0.0, (now - min(waiting.values())).total_seconds())

       def pending(self, seat: str) -> int:
           return len(self._seen.get(seat, {}))
   ```
   `trim` is one method beyond the design sheet: nothing reports a start to the backlog across processes (`--role router` and `--role seat`), and without it `pending` and the oldest age would grow forever. The depth is the queue's own count, so trimming to it keeps the ages true in every role.
2. **`class ResidentSeatScheduler`**, built with keyword arguments:
   `ResidentSeatScheduler(*, loop_id: LoopId, hosts: Mapping[str, SeatHostInterface], models: Mapping[str, str], default_seat: str, amqp: AmqpClientInterface, names: RunQueueNamesInterface, runtime: ModelRuntimeInterface, schedule: ResidencyScheduleInterface, backlog: SeatBacklogInterface, config: LoopConfigInterface, clock: Clock, measurements: LoopMeasurementLogInterface, logger: Logger | None = None)`.
   `hosts` and `models` are keyed by seat slug (`models` maps a slug to its model name). The constructor raises `ValueError(f"the default seat {default_seat} has no seat host")` when `default_seat not in hosts`, and `ValueError("every seat needs both a host and a model")` when `set(models) != set(hosts)`. It keeps `self._resident = default_seat`, `self._runs_since_switch = 0` and `self._stopping = asyncio.Event()`. Class constant `POLL_SECONDS = 0.05`.
3. Properties `resident_seat -> str` and `resident_model -> str` (`models[resident_seat]`).
4. **`async start(self) -> None`**:
   ```python
   for host in self._hosts.values():
       await host.declare()
   loaded = await self._runtime.loaded()
   resident = [seat for seat, model in self._models.items() if loaded is not None and model in loaded]
   self._resident = self._default if self._default in resident or not resident else resident[0]
   await self._hosts[self._resident].consume()
   self._log.info(
       "resident_seat_chosen",
       loop=self._loop_id.value,
       seat=self._resident,
       model=self.resident_model,
       loaded=None if loaded is None else list(loaded),
   )
   ```
   So: a loaded default wins; else the first loaded declared model in `hosts` order; else the default (also when the runtime does not answer, D1). Only the resident host consumes.
5. **`async on_run_finished(self, seat: str) -> None`**: when `seat == self._resident`, `self._runs_since_switch += 1`; then `await self.tick()`. (The composition wires it with `host.set_on_run_finished(scheduler.on_run_finished)` for every host.)
6. **`async tick(self) -> str | None`** — returns the new resident seat when it switched, else `None`:
   ```python
   now = self._clock.now()
   loads: list[SeatLoad] = []
   for seat in self._hosts:
       depth = await self._amqp.queue_depth(self._names.seat_queue(self._loop_id, seat)) or 0
       self._backlog.trim(seat, depth)
       loads.append(
           SeatLoad(seat=seat, depth=depth, oldest_wait_seconds=self._backlog.oldest_wait_seconds(seat, now))
       )
   target = self._schedule.next_seat(
       resident=self._resident,
       resident_busy=self._hosts[self._resident].busy,
       runs_since_switch=self._runs_since_switch,
       loads=loads,
       max_wait_seconds=float(self._config.residency_max_wait_seconds),
       min_hold_runs=self._config.residency_min_hold_runs,
   )
   if target is None:
       return None
   await self._switch(target)
   return target
   ```
   (`queue_depth` is `None` for a queue not declared yet, which counts as 0.)
7. **`_switch(self, target: str) -> None`** — cancel first, so nothing new starts on the old seat; wait out a run that slipped in before the cancel; then unload; then consume:
   ```python
   previous = self._resident
   old = self._hosts[previous]
   await old.cancel()
   while old.busy:
       await asyncio.sleep(self.POLL_SECONDS)
   unload_ms: float | None = None
   if self._config.unload_on_switch:
       began = time.monotonic()
       unloaded = await self._runtime.unload(self._models[previous])
       unload_ms = (time.monotonic() - began) * 1000
       self._log.info("resident_model_unloaded", model=self._models[previous], unloaded=unloaded)
   await self._hosts[target].consume()
   self._resident = target
   self._runs_since_switch = 0
   self._measurements.record(
       LoopMeasurement(
           loop_id=self._loop_id,
           subject=MeasurementSubject.SWITCH,
           at=self._clock.now(),
           seat=target,
           model=self._models[target],
           latency_ms=unload_ms,
           outcome=f"{previous}->{target}",
       )
   )
   self._log.info("resident_seat_switched", loop=self._loop_id.value, previous=previous, resident=target)
   ```
   (The design sheet orders "wait until not busy → cancel"; cancelling first closes the window in which a new delivery could start on the old seat between the wait and the cancel.)
8. **`async run_forever(self) -> None`** ticks every `config.schedule_interval_seconds` until `stop()`:
   ```python
   while not self._stopping.is_set():
       with contextlib.suppress(TimeoutError):
           await asyncio.wait_for(
               self._stopping.wait(), timeout=float(self._config.schedule_interval_seconds)
           )
       if not self._stopping.is_set():
           await self.tick()
   ```
   **`async stop(self) -> None`** sets the event (draining the hosts is the process's job).
9. **Interfaces** in `src/vibey/infrastructure/loop_service/interfaces/resident_schedule_interface.py`, both `@runtime_checkable`, one-line docstring per member:
   - `SeatBacklogInterface`: `forwarded(self, seat: str, run_id: UUID, at: datetime) -> None`, `started(self, seat: str, run_id: UUID) -> None`, `trim(self, seat: str, depth: int) -> None`, `oldest_wait_seconds(self, seat: str, now: datetime) -> float | None`, `pending(self, seat: str) -> int`.
   - `ResidentSeatSchedulerInterface`: properties `resident_seat -> str`, `resident_model -> str`; `async start(self) -> None`, `async on_run_finished(self, seat: str) -> None`, `async tick(self) -> str | None`, `async run_forever(self) -> None`, `async stop(self) -> None`.
10. **Fake**, appended to `tests/fakes/loops.py`:
    ```python
    class FakeResidentScheduler:
        """ResidentSeatSchedulerInterface in memory: `next_seat` scripts the next switch."""

        def __init__(
            self,
            *,
            resident_seat: str = "gpt-oss-20b",
            resident_model: str = "gpt-oss:20b",
            next_seat: str | None = None,
        ) -> None:
            self._resident_seat = resident_seat
            self._resident_model = resident_model
            self.next_seat = next_seat
            self.started = False
            self.finished: list[str] = []
            self.ticks = 0
            self._stopping = asyncio.Event()

        @property
        def resident_seat(self) -> str:
            return self._resident_seat

        @property
        def resident_model(self) -> str:
            return self._resident_model

        async def start(self) -> None:
            self.started = True

        async def on_run_finished(self, seat: str) -> None:
            self.finished.append(seat)
            await self.tick()

        async def tick(self) -> str | None:
            self.ticks += 1
            target, self.next_seat = self.next_seat, None
            if target is not None:
                self._resident_seat = target
            return target

        async def run_forever(self) -> None:
            await self._stopping.wait()

        async def stop(self) -> None:
            self._stopping.set()
    ```
11. **Registry**: `SeatBacklogInterface` and `ResidentSeatSchedulerInterface` are appended to `DRIVER_SEAMS`; `REGISTRY` gains `FakeRegistration(port=SeatBacklogInterface, build=SeatBacklog, note="production in-memory: the backlog lives in memory by design (ADR-0046 §4)")` and `FakeRegistration(port=ResidentSeatSchedulerInterface, build=FakeResidentScheduler)`.

## Where to change
Line 1 of every new file is the provenance comment, copied byte for byte from line 1 of `src/vibey/infrastructure/process/reaper.py`.
- **New** `src/vibey/infrastructure/loop_service/resident_schedule.py` (behaviours 1–8). Imports: `asyncio`, `contextlib`, `time`, `from collections.abc import Mapping`, `from datetime import datetime`, `from uuid import UUID`, `structlog`, `from vibey_bootstrap.amqp.interfaces import AmqpClientInterface`, `from vibey.application.interfaces import Clock, Logger`, `from vibey.domain.interfaces.loop_services_config_interface import LoopConfigInterface`, `from vibey.domain.interfaces.residency_interface import ResidencyScheduleInterface`, `from vibey.domain.interfaces.run_protocol_interface import RunQueueNamesInterface`, `from vibey.domain.loop import LoopId`, `from vibey.domain.loop_events import LoopMeasurement, MeasurementSubject`, `from vibey.domain.residency import SeatLoad`, `from vibey.infrastructure.loop_service.interfaces.measurement_log_interface import LoopMeasurementLogInterface`, `from vibey.infrastructure.loop_service.interfaces.model_runtime_interface import ModelRuntimeInterface`, `from vibey.infrastructure.loop_service.interfaces.resident_schedule_interface import SeatBacklogInterface`, `from vibey.infrastructure.loop_service.interfaces.seat_host_interface import SeatHostInterface`. `__all__ = ["ResidentSeatScheduler", "SeatBacklog"]`. `time.monotonic()` measures the unload's wall duration only; every decision reads the injected clock.
- **New** `src/vibey/infrastructure/loop_service/interfaces/resident_schedule_interface.py` (behaviour 9), in the style of `src/vibey/infrastructure/process/interfaces/reaper_interface.py`.
- **`tests/fakes/loops.py`**: add `import asyncio` if missing; append the class of behaviour 10 at the end with `edit_file`.
- **`tests/fakes/registry.py`**: run the registration script of lane `loops-result-store` (the `register_fakes.py` block) with only these lists, then delete the script:
  ```python
  IMPORTS = [
      "from tests.fakes.loops import FakeResidentScheduler",
      "from vibey.infrastructure.loop_service.interfaces.resident_schedule_interface import ResidentSeatSchedulerInterface, SeatBacklogInterface",
      "from vibey.infrastructure.loop_service.resident_schedule import SeatBacklog",
  ]
  SEAMS = ["SeatBacklogInterface", "ResidentSeatSchedulerInterface"]
  ENTRIES = [
      'FakeRegistration(port=SeatBacklogInterface, build=SeatBacklog, note="production in-memory: the backlog lives in memory by design (ADR-0046 §4)")',
      "FakeRegistration(port=ResidentSeatSchedulerInterface, build=FakeResidentScheduler)",
  ]
  ```
- Then `uv run ruff check --fix` and `uv run ruff format` on `src/vibey/infrastructure/loop_service tests/fakes/loops.py tests/fakes/registry.py tests/infrastructure/loop_service`.
- **New** `tests/infrastructure/loop_service/test_resident_schedule.py`.

## Acceptance criteria
- [ ] Only the resident seat's host consumes; every host is declared at start.
- [ ] A switch cancels the old seat, waits out a run that slipped in, unloads the old model (unless `unload_on_switch` is false), consumes the new seat, and records one SWITCH measurement — never two models loaded at once.
- [ ] No switch while the resident is busy; the starvation bound switches after `residency_max_wait_seconds` once `residency_min_hold_runs` runs have finished.
- [ ] With no answering runtime the schedule starts on the default seat (D1).
- [ ] No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`; `tests/meta/patching_baseline.json` does not change; `tests/fakes/test_port_parity.py` passes (including the not-a-stub check on the production `SeatBacklog`).
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_resident_schedule.py`. Seats: `A = "gpt-oss-20b"` (model `"gpt-oss:20b"`, the default) and `B = "qwen3-coder-30b"` (model `"qwen3-coder:30b"`). Hosts are `FakeSeatHost(seat=A, model="gpt-oss:20b")` and `FakeSeatHost(seat=B, model="qwen3-coder:30b")`; the runtime is `FakeModelRuntime(...)`; the policy is the real `ResidencySchedule()`; the backlog the real `SeatBacklog()`; measurements `InMemoryLoopMeasurementLog()`; the clock a local `_Clock` (the same four-line class as in `test_seat_host_core.py`) at `NOW = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)`; config `LoopConfig()` or `dataclasses.replace(LoopConfig(), ...)`. The broker is an `InMemoryAmqpClient` on which the **test** declares both seat queues (`names.seat_queue(LoopId.SOVEREIGNLOOP, seat)`) and binds them to a direct exchange, so that publishing into a seat queue gives it depth (the fake hosts consume nothing).
- `test_start_declares_every_seat_and_consumes_only_the_resident`: `FakeModelRuntime(())`; after `start()`, `hosts[A].calls == ["declare", "consume"]`, `hosts[B].calls == ["declare"]`; `resident_seat == A`, `resident_model == "gpt-oss:20b"`.
- `test_start_prefers_the_loaded_default_then_any_loaded_model`: `FakeModelRuntime(("qwen3-coder:30b",))` → resident `B`; `FakeModelRuntime(("qwen3-coder:30b", "gpt-oss:20b"))` → resident `A`.
- `test_start_without_an_answering_runtime_uses_the_default` (D1): `FakeModelRuntime(None)` → resident `A`, consuming.
- `test_an_empty_resident_seat_switches_to_a_seat_with_work`: after `start()`, publish one message into seat `B`; `await tick() == B`; `hosts[A].calls[-1] == "cancel"`, `hosts[B].consuming is True`; `runtime.unloads == ["gpt-oss:20b"]`; one SWITCH measurement with `seat == B`, `model == "qwen3-coder:30b"`, `outcome == f"{A}->{B}"` and `latency_ms >= 0`.
- `test_no_switch_while_the_resident_is_busy`: `hosts[A].busy = True`, seat `B` has work → `await tick() is None`, no unload.
- `test_the_starvation_bound_switches_after_max_wait_and_min_hold`: both seats have one message; `backlog.forwarded(B, uuid4(), NOW - timedelta(seconds=901))`; `await tick() is None` (no run finished since the switch); `await scheduler.on_run_finished(A)` switches to `B`. In a second scheduler, a wait of 899 s never switches.
- `test_on_run_finished_counts_only_the_residents_runs`: `on_run_finished(B)` while `A` is resident ticks but does not count: with both seats holding work and `B`'s oldest wait past 900 s, no switch happens; `on_run_finished(A)` then switches.
- `test_unload_on_switch_can_be_turned_off`: `unload_on_switch=False` → the switch happens, `runtime.unloads == []`, the SWITCH measurement's `latency_ms is None`.
- `test_a_switch_waits_for_a_run_that_slipped_in`: host `A` is an instance of a test-local subclass of `FakeSeatHost` whose `cancel` also sets `busy = True` and schedules `busy = False` with `asyncio.get_running_loop().call_later(0.1, ...)`; with seat `B` holding work and `A` none, `began = asyncio.get_running_loop().time()`; `await tick() == B` returns no sooner than `began + 0.1`; afterwards `hosts[A].busy is False` and `runtime.unloads == ["gpt-oss:20b"]`.
- `test_run_forever_ticks_until_stopped`: `schedule_interval_seconds=0.01`; seat `B` has work, `A` none; `task = asyncio.create_task(scheduler.run_forever())`; poll until `resident_seat == B` (at most 2 s); `await scheduler.stop()`; `await task` finishes.
- `test_backlog_ages_from_the_first_forward_and_trims_to_depth`: `forwarded(B, r1, NOW - 30 s)`, `forwarded(B, r1, NOW - 5 s)` (kept at −30 s), `forwarded(B, r2, NOW - 20 s)`, `forwarded(B, r3, NOW - 10 s)`: `pending(B) == 3`, `oldest_wait_seconds(B, NOW) == 30.0`; `trim(B, 1)` leaves only `r3` (`oldest == 10.0`); `started(B, r3)` empties it (`oldest is None`, `pending == 0`); an unknown seat gives `None` and `0`; a `now` earlier than the entry gives `0.0`.
- `test_the_scheduler_refuses_a_default_without_a_host_or_mismatched_models`: `ValueError` for `default_seat="nope"`, and for `models` missing `B`.
- `test_classes_and_fakes_satisfy_their_interfaces`: `isinstance` of the scheduler and `FakeResidentScheduler()` against `ResidentSeatSchedulerInterface`, of `SeatBacklog()` against `SeatBacklogInterface`. `FakeResidentScheduler(next_seat=B)`: `await tick() == B` then `None`; `on_run_finished(A)` records `[A]`; `run_forever()` ends after `stop()`.

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
- Routing (the router reads `resident_model` and the backlog: lanes `loops-router-routing`, `loops-router-forwarding`); probes that must not load a model (lane `loops-probe-consumer`).
- Wiring the callbacks, choosing `--role all` versus `--role seat` (D6) and logging `seat_runtime_unreachable` (D1): lanes `loops-service-process` and `loops-bootstrap-loop-service`.
- V-OLL2 (Ollama evicts rather than overflows on a 24 GB machine): recorded evidence for the operator, not a unit test.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Protected tests are never edited.
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject. Follow `STORM/EDITING-RULES.md`.

**Depends on:** `loops-seat-host-drain`, `loops-residency-schedule`, `loops-model-runtime`
- `loops-seat-host-drain`: `SeatHostInterface` with `busy` and `set_on_run_finished`, and `FakeSeatHost` with a settable `busy`.
- `loops-residency-schedule`: `ResidencySchedule`, `ResidencyScheduleInterface`, `SeatLoad`.
- `loops-model-runtime`: `ModelRuntimeInterface` and `FakeModelRuntime`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
