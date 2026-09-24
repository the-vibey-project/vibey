## Title
feat(loop-service): the seat host streams progress, takes control commands and drains on stop
ADR-0046 lane L28c (slug `loops-seat-host-drain`).

## Why
Draft ADR-0046 §3 (`STORM/specs/ADR-two-loops.md:158-167`) keeps ADR-0044's `vibey.run.progress/1` reply ("as in ADR-0044"), and the superseded host's behaviour 3h and 5 (`specs/rmq-r22-loop-service-host.md`; closing note `issue-audit/updates/369.md`) specify it: one `RunProgress` per new `events.jsonl` line when `publish_progress` is on and there is a run directory, polled every 0.5 s, `seq` from 1; and a drain that "cancels the consumer and lets active runs finish for up to `grace_seconds`. It then stops the runs still going; each one's result is `ABANDONED`, written, published and completed." ADR-0046 §11 runs each loop Deployment with `strategy: Recreate`, so this drain is what a rollout or a SIGTERM runs (the CLI lane exits 0 after it, decision D3).

The other loop-service parts need handles on a running seat host: the control consumer (lane `loops-control-and-dead-letters`) routes stop, wind-down and prompts to the host holding a run, and the `SUPERSEDE` broadcast to every host ("The router also honours a `SUPERSEDE` control broadcast by stopping any lower attempt it holds", §6); the resident schedule (lane `loops-resident-schedule`, §4) switches models only between runs, so it needs `busy` and a callback when a run has ended. Lanes `loops-seat-host-core` and `loops-seat-host-fence` wrote `seat_host.py`; this lane edits it at the anchors below. 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`): an abandoned run is measured like any run (subject RUN, outcome `abandoned:<code>`).

## Required behaviour
1. **Progress.** While a run is going, when `config.publish_progress` is true and `request.run_dir` is set, a `_ProgressPump` task polls `Path(request.cwd) / request.run_dir / "events.jsonl"` every `progress_interval_seconds` (a new constructor keyword, default `0.5`) and publishes each new **complete** line (bytes up to `\n`, decoded UTF-8 with `errors="replace"`, without the newline) as `RunProgress(run_id, seq, line)` to `reply_to`, `seq` counting from 1. A trailing partial line waits for its newline. A missing file publishes nothing. When the run ends, the pump reads the file one last time, then stops; every progress reply precedes the `RunResult`.
2. **`busy -> bool`** (property): true while any run is registered in the host (from just before its spawn until its result is acknowledged).
3. **`active_run_ids(self) -> tuple[UUID, ...]`**: the run ids registered, in start order.
4. **`control(self, run_id: UUID, command: RunControlCommand, text: str | None) -> bool`**: when the run is registered and spawned, `run.control(command, text)`'s answer; otherwise `False`.
5. **`stop_lower_attempts(self, key: str, attempt: int) -> tuple[UUID, ...]`**: sends `STOP` (`run.control(RunControlCommand.STOP, None)`) to every spawned run whose `request.supersedes` has this `key` and a lower `attempt`, and returns their run ids; logs `info("seat_lower_attempts_stopped", seat, key, attempt, run_ids)`. The run then ends on its own and its result is persisted as usual.
6. **`set_on_run_finished(self, callback: Callable[[str], Awaitable[None]] | None) -> None`**: after every run this host **started** has ended, been answered, acknowledged and removed from `busy`, the host awaits `callback(self.seat)`. Refusals, rejections and republished results do not call it. (A setter, not a constructor keyword: the resident schedule is built after its hosts.)
7. **`async stop(self, grace_seconds: float) -> None`** — the drain: `cancel()` the consumer; wait until no run is registered, at most `grace_seconds`; then mark every spawned run still registered as abandoned and `run.stop(config.supersede_grace_seconds)` it; wait again, at most `supersede_grace_seconds`; log `info("seat_drained", seat, abandoned=[run ids], remaining=<count>)`. An abandoned run's own handler builds its result with `status=ABANDONED`, `detail="the seat host stopped before the run finished"` and the exit code its stop produced, then persists, publishes and acknowledges it as usual, and records the RUN measurement (`outcome == "abandoned:<code>"`).
8. **Interface.** `SeatHostInterface` gains `busy` (property), `active_run_ids`, `control`, `stop_lower_attempts`, `set_on_run_finished` and `stop`, with those signatures and a one-line docstring each; **`FakeSeatHost`** gains the same members (behaviour 9), so the registry's signature test keeps passing.
9. **Fake additions**, in `tests/fakes/loops.py`, inside `FakeSeatHost`:
   - in `__init__`, after `self.calls: list[str] = []`:
     ```python
             self._busy = False
             self.active: list[UUID] = []
             self.controls: list[tuple[UUID, RunControlCommand, str | None]] = []
             self.lower_attempt_stops: list[tuple[str, int]] = []
             self.stops: list[float] = []
             self.on_run_finished: Callable[[str], Awaitable[None]] | None = None
     ```
   - new members, after its `start` method:
     ```python
         @property
         def busy(self) -> bool:
             return self._busy

         @busy.setter
         def busy(self, value: bool) -> None:
             self._busy = value

         def active_run_ids(self) -> tuple[UUID, ...]:
             return tuple(self.active)

         def control(self, run_id: UUID, command: RunControlCommand, text: str | None) -> bool:
             self.controls.append((run_id, command, text))
             return run_id in self.active

         def stop_lower_attempts(self, key: str, attempt: int) -> tuple[UUID, ...]:
             self.lower_attempt_stops.append((key, attempt))
             return tuple(self.active)

         def set_on_run_finished(self, callback: Callable[[str], Awaitable[None]] | None) -> None:
             self.on_run_finished = callback

         async def stop(self, grace_seconds: float) -> None:
             self.stops.append(grace_seconds)
             await self.cancel()

         async def finish_run(self) -> None:
             """Test helper: a run on this seat ended; call the callback as SeatHost does."""
             self._busy = False
             if self.on_run_finished is not None:
                 await self.on_run_finished(self._seat)
     ```

## Where to change
`src/vibey/infrastructure/loop_service/seat_host.py` and `interfaces/seat_host_interface.py`, `tests/fakes/loops.py`, and the new test file. `seat_host.py` and `tests/fakes/loops.py` are longer than 100 lines: `edit_file` only. Each anchor is text lanes `loops-seat-host-core` and `loops-seat-host-fence` wrote; if one is not found verbatim (formatting may have re-wrapped a line), `read_file` the method and insert at the described point.
- **Imports** of `seat_host.py`: add `import asyncio`, `import contextlib`; extend `from collections.abc import Mapping` to `from collections.abc import Awaitable, Callable, Mapping`; add `RunControlCommand` and `RunProgress` to the `from vibey.domain.run_protocol import ...` line.
- **`_ActiveRun`**: after its line `    run: LocalRunInterface | None = None` add `    abandoned: bool = False`.
- **`_ProgressPump`**: insert this class right before the line `class SeatHost:`:
  ```python
  class _ProgressPump:
      """Publishes each new complete line of a run's `events.jsonl` as a RunProgress, in
      order, with `seq` from 1 (ADR-0046 §3, `vibey.run.progress/1`)."""

      def __init__(
          self,
          *,
          path: Path,
          publish: Callable[[RunProgress], Awaitable[None]],
          run_id: UUID,
          interval_seconds: float,
      ) -> None:
          self._path = path
          self._publish = publish
          self._run_id = run_id
          self._interval = interval_seconds
          self._offset = 0
          self._seq = 0
          self._pending = b""

      async def pump_once(self) -> None:
          try:
              with self._path.open("rb") as handle:
                  handle.seek(self._offset)
                  chunk = handle.read()
          except FileNotFoundError:
              return
          self._offset += len(chunk)
          *lines, self._pending = (self._pending + chunk).split(b"\n")
          for line in lines:
              self._seq += 1
              await self._publish(
                  RunProgress(
                      run_id=self._run_id,
                      seq=self._seq,
                      line=line.decode("utf-8", errors="replace"),
                  )
              )

      async def run(self, stop: asyncio.Event) -> None:
          while not stop.is_set():
              await self.pump_once()
              with contextlib.suppress(TimeoutError):
                  await asyncio.wait_for(stop.wait(), timeout=self._interval)
          await self.pump_once()
  ```
- **Constructor parameter.** `old_string`:
  ```
          fence: WorktreeFenceInterface | None = None,
          logger: Logger | None = None,
  ```
  `new_string`: the same with `        progress_interval_seconds: float = 0.5,` inserted before the `logger` line.
- **Constructor body.** After the line `        self._active: dict[UUID, _ActiveRun] = {}` add:
  ```python
          self._progress_interval = progress_interval_seconds
          self._on_run_finished: Callable[[str], Awaitable[None]] | None = None
  ```
- **Progress and abandon in `_run`.** `old_string`:
  ```
              exit_code = await run.wait(float(request.deadline_seconds))
              if exit_code is None:
                  await run.stop(float(self._config.supersede_grace_seconds))
                  status = RunStatus.DEADLINE_EXCEEDED
                  detail = f"run exceeded its deadline of {request.deadline_seconds}s"
              else:
                  status = RunStatus.EXITED
                  detail = ""
              stdout, stderr = run.output()
  ```
  `new_string`:
  ```python
              stop_progress = asyncio.Event()
              progress = self._start_progress(entry, stop_progress)
              try:
                  exit_code = await run.wait(float(request.deadline_seconds))
                  if exit_code is None:
                      await run.stop(float(self._config.supersede_grace_seconds))
                      status = RunStatus.DEADLINE_EXCEEDED
                      detail = f"run exceeded its deadline of {request.deadline_seconds}s"
                  else:
                      status = RunStatus.EXITED
                      detail = ""
              finally:
                  stop_progress.set()
                  if progress is not None:
                      await progress
              if entry.abandoned:
                  status = RunStatus.ABANDONED
                  detail = "the seat host stopped before the run finished"
              stdout, stderr = run.output()
  ```
- **The callback.** `old_string`:
  ```
          finally:
              self._active.pop(request.run_id, None)
              self._fence.release(Path(request.cwd), request.run_id)
  ```
  `new_string`:
  ```python
          finally:
              self._active.pop(request.run_id, None)
              self._fence.release(Path(request.cwd), request.run_id)
          if self._on_run_finished is not None:
              # Only reached when the run started and ended: it has left `busy` by now, so
              # the resident schedule sees this host idle (ADR-0046 §4).
              await self._on_run_finished(self._seat)
  ```
- **New members**, inserted right after `SeatHost.start` (`old_string`: `    async def start(self) -> None:\n        await self.declare()\n        await self.consume()\n` — in `seat_host.py` this text is unique):
  ```python
      @property
      def busy(self) -> bool:
          return bool(self._active)

      def active_run_ids(self) -> tuple[UUID, ...]:
          return tuple(self._active)

      def control(self, run_id: UUID, command: RunControlCommand, text: str | None) -> bool:
          entry = self._active.get(run_id)
          if entry is None or entry.run is None:
              return False
          return entry.run.control(command, text)

      def stop_lower_attempts(self, key: str, attempt: int) -> tuple[UUID, ...]:
          stopped: list[UUID] = []
          for entry in list(self._active.values()):
              supersedes = entry.request.supersedes
              if (
                  entry.run is None
                  or supersedes is None
                  or supersedes.key != key
                  or supersedes.attempt >= attempt
              ):
                  continue
              entry.run.control(RunControlCommand.STOP, None)
              stopped.append(entry.request.run_id)
          self._log.info(
              "seat_lower_attempts_stopped",
              seat=self._seat,
              key=key,
              attempt=attempt,
              run_ids=[str(run_id) for run_id in stopped],
          )
          return tuple(stopped)

      def set_on_run_finished(self, callback: Callable[[str], Awaitable[None]] | None) -> None:
          self._on_run_finished = callback

      async def stop(self, grace_seconds: float) -> None:
          await self.cancel()
          await self._wait_idle(grace_seconds)
          running = [
              (entry, entry.run) for entry in list(self._active.values()) if entry.run is not None
          ]
          for entry, run in running:
              entry.abandoned = True
              await run.stop(float(self._config.supersede_grace_seconds))
          await self._wait_idle(float(self._config.supersede_grace_seconds))
          self._log.info(
              "seat_drained",
              seat=self._seat,
              abandoned=[str(entry.request.run_id) for entry, _ in running],
              remaining=len(self._active),
          )

      async def _wait_idle(self, timeout: float) -> None:
          loop = asyncio.get_running_loop()
          deadline = loop.time() + timeout
          while self._active and loop.time() < deadline:
              await asyncio.sleep(0.01)

      def _start_progress(
          self, entry: _ActiveRun, stop: asyncio.Event
      ) -> asyncio.Task[None] | None:
          request = entry.request
          if not self._config.publish_progress or request.run_dir is None:
              return None
          pump = _ProgressPump(
              path=Path(request.cwd) / request.run_dir / "events.jsonl",
              publish=lambda progress: self._reply(entry.delivery, request.run_id, progress),
              run_id=request.run_id,
              interval_seconds=self._progress_interval,
          )
          return asyncio.create_task(pump.run(stop))
  ```
  (The progress replies go to `entry.delivery`, so a rebound delivery keeps its `reply_to`.)
- **`interfaces/seat_host_interface.py`**: add the six members of behaviour 8 to `SeatHostInterface` (imports `from collections.abc import Awaitable, Callable`, `from uuid import UUID`, `from vibey.domain.run_protocol import RunControlCommand`).
- **`tests/fakes/loops.py`**: add `from collections.abc import Awaitable, Callable` (and `RunControlCommand`, `UUID` if missing) to its imports; make the two edits of behaviour 9. For the second, use this unique `old_string` (the end of `FakeSeatHost`):
  ```
      async def cancel(self) -> None:
          self.calls.append("cancel")
          self._consuming = False

      async def start(self) -> None:
          await self.declare()
          await self.consume()
  ```
  and append the new members after it.
- Then `uv run ruff check --fix` and `uv run ruff format` on `src/vibey/infrastructure/loop_service tests/fakes/loops.py tests/infrastructure/loop_service`.
- **New** `tests/infrastructure/loop_service/test_seat_host_drain.py`. Line 1 is the provenance comment, copied byte for byte from line 1 of `src/vibey/infrastructure/process/reaper.py`.

## Acceptance criteria
- [ ] `tests/infrastructure/loop_service/test_seat_host_core.py` and `test_seat_host_fence.py` pass **unedited**.
- [ ] Progress replies arrive in file order, `seq` 1, 2, 3…, all before the `RunResult`; a partial last line is published only once completed.
- [ ] The drain lets a run that ends within the grace end normally, and answers a run still going with a persisted, published, acknowledged `ABANDONED` result; after it, the host consumes nothing.
- [ ] The run-finished callback sees `busy is False`, and is not called for a refused request.
- [ ] `tests/fakes/test_port_parity.py` passes (the fake has every new member, with the same parameter names). No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`; `tests/meta/patching_baseline.json` does not change.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_seat_host_drain.py`. Copy the helpers `NOW`, `SEAT`, `MODEL`, `REPLIES`, `_Clock`, `_Rig`, `_request`, `_send` and `_replies` from `test_seat_host_core.py`, and give `_rig` two more keywords passed through to `SeatHost`: `config: LoopConfig | None = None` (default `LoopConfig()`) and `progress_interval_seconds: float = 0.01`. A background run is `task = asyncio.create_task(_send(rig, body))`, then `for _ in range(200): if rig.executor.runs: break; await asyncio.sleep(0.01)`. Every test ends with no pending task (finish the fake run and `await task`).
- `test_progress_lines_are_published_in_order_from_seq_1`: `FakeLocalRunExecutor(hang=True)`, `run_dir=".sovereignloop/runs/r1"`, which does **not** exist when the request arrives (a run directory that already exists without a terminal `meta.json` is abandoned by rule d; the runner creates its own). Start the run; then create the directory and write `events.jsonl` holding `b'{"n": 1}\n{"n": 2}\n'`; wait until two `RunProgress` messages are among the bodies in `rig.amqp.published` (decode each body with the codec); append `b'{"n": 3}'` (no newline), sleep 0.05 s, append `b"\n"`; finish with `rig.executor.runs[0].finish(0)` and `await task`. `_replies(rig)` is `RunAccepted`, then `RunProgress` with `seq` 1, 2, 3 and lines `{"n": 1}`, `{"n": 2}`, `{"n": 3}`, then the `RunResult` (`EXITED`).
- `test_no_progress_when_disabled`: `config=dataclasses.replace(LoopConfig(), publish_progress=False)`; the run directory exists beforehand with `meta.json` holding `{"status": "finished"}` (so rule d lets it run) and an `events.jsonl` of two lines; a run that exits at once → replies are only `RunAccepted` and `RunResult`.
- `test_no_progress_without_an_events_file`: `run_dir` set, the directory created with a finished `meta.json` but no `events.jsonl` → only `RunAccepted` and `RunResult`.
- `test_busy_and_active_run_ids_follow_the_run`: before: `busy is False`, `active_run_ids() == ()`; while a hanging run goes: `busy is True`, `active_run_ids() == (run_id,)`; after it ends: back to `False` and `()`.
- `test_control_reaches_only_an_active_run`: while a hanging run with a `run_dir` goes, `rig.host.control(run_id, RunControlCommand.PROMPT_NOW, "hi") is True` and the fake run's `controls == [(PROMPT_NOW, "hi")]`; `rig.host.control(uuid4(), RunControlCommand.STOP, None) is False`.
- `test_stop_lower_attempts_stops_only_lower_attempts_of_the_key`: a hanging run with `supersedes=RunSupersede(key="job-1", attempt=0)`: `stop_lower_attempts("job-1", 0) == ()`, `stop_lower_attempts("job-2", 5) == ()`, then `stop_lower_attempts("job-1", 1) == (run_id,)` and the fake run's `controls == [(RunControlCommand.STOP, None)]`. After that run is finished and awaited, a second hanging run with no `supersedes` gives `stop_lower_attempts("job-1", 9) == ()`, and its fake run has no controls.
- `test_on_run_finished_is_awaited_after_the_run_left_busy`: `seen: list[tuple[str, bool]] = []`; a callback `async def finished(seat: str) -> None: seen.append((seat, rig.host.busy))` set with `set_on_run_finished`; one run → `seen == [(SEAT, False)]`; a late request (`start_by` in the past) → `seen` unchanged; after `set_on_run_finished(None)` another run leaves `seen` unchanged.
- `test_drain_lets_a_run_that_ends_within_grace_end_normally`: a hanging run; `asyncio.get_running_loop().call_later(0.05, rig.executor.runs[0].finish, 0)`; `await rig.host.stop(2.0)`; `await task`; the result is `EXITED` with `exit_code == 0`; `rig.host.consuming is False`.
- `test_drain_abandons_runs_still_going_after_grace`: a hanging run; `await rig.host.stop(0.05)`; `await task`; the result is `ABANDONED`, detail `"the seat host stopped before the run finished"`, `exit_code == -9`; it is persisted (`rig.results.read(...)`); `rig.executor.runs[0].stops == [30.0]`; the last measurement is RUN with outcome `"abandoned:-9"`; a request sent afterwards stays in the seat queue (`await rig.amqp.queue_depth(seat_queue) == 1`).
- `test_the_fake_seat_host_has_every_new_member`: `FakeSeatHost()`: `busy` is settable; `active` drives `active_run_ids`, `control` (recorded, true only for an active id) and `stop_lower_attempts`; `await stop(1.0)` records `[1.0]` and stops consuming; `finish_run()` awaits a set callback with the seat and clears `busy`; `isinstance(FakeSeatHost(), SeatHostInterface)`.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/fakes tests/meta/test_patching_ratchet.py
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
# after the local commit, this must print nothing:
git diff --stat HEAD~1 -- tests/infrastructure/loop_service/test_seat_host_core.py tests/infrastructure/loop_service/test_seat_host_fence.py
```
Nothing here is OS-specific (8.h: Arch Linux and macOS alike).

## Out of scope
- The control consumer, the dead-letter replier and the probe consumer that call these members (lanes `loops-control-and-dead-letters`, `loops-probe-consumer`).
- The resident schedule that sets the callback (lane `loops-resident-schedule`), and the process and CLI that call `stop` on SIGTERM (lanes `loops-service-process`, `loops-cli-loop-service`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Protected tests are never edited.
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject. Follow `STORM/EDITING-RULES.md`.

**Depends on:** `loops-seat-host-fence`
- `loops-seat-host-fence`: the `seat_host.py` text this lane anchors on (core plus fence).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
