## Title
feat(loop-service): the seat host rebinds a redelivered run, abandons a crashed one, and takes the worktree fence
ADR-0046 lane L28b (slug `loops-seat-host-fence`).

## Why
Draft ADR-0046's idempotency table (`/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-two-loops.md:183-191`) gives the seat host the "a run" row ("an active run is rebound, a persisted result is re-sent, a non-terminal run directory is abandoned") and the worktree fence the "run ownership" row, "across both loops". §6 (lines 238–253) spells out the fence's outcomes and says "the seat host acquires the lock before it starts a run, and releases it after the result is persisted". The superseded host's rules b and d carry over unchanged (`specs/rmq-r22-loop-service-host.md`, behaviour 3; closing note `issue-audit/updates/369.md`); its rule g, which ADR-0046 *Context* (lines 55–58) shows could not supersede at prefetch 1 and guarded only one instance, is replaced by the fence of lane `loops-worktree-fence`. Sub-doctrine 8.c's replay rule (`src/vibey_tools/gh/docs/doctrines.md:196-234`): a message delivered twice is answered once. 8.g (`:316-324`): every refusal is measured (subject REJECT).

Lane `loops-seat-host-core` wrote `seat_host.py` in full; this lane edits it at the anchors below.

## Required behaviour
1. **Constructor.** `SeatHost` gains the keyword `fence: WorktreeFenceInterface | None = None` (between `prefetch` and `logger`). When it is `None`, the host builds the production fence: `WorktreeFence(stale_after=timedelta(seconds=config.stale_lock_seconds), clock=clock, logger=logger)`.
2. **Rule b — a redelivery of an active run** (checked right after the message is known to be a run request for this loop, before anything else): when `request.run_id` is in `self._active`, the entry's `delivery` becomes the new delivery, `info("seat_run_rebound", seat, run_id)` is logged, and nothing is started, replied or settled. The running run settles the new delivery when it ends (the core already settles `entry.delivery`).
3. **Rule d — a run directory left non-terminal** (checked after the persisted-result check c, before the `start_by` check e): when `request.run_dir` is set, `Path(request.cwd) / request.run_dir` is a directory, and its `meta.json` status (`None` when the file is missing, unreadable, not a JSON object or has no string `status`) is not one of `finished`, `failed`, `stopped`, the host answers without running: a `RunResult` with `status=ABANDONED`, `exit_code=None`, `meta_status=None`, `started_at=None`, `detail="run directory left non-terminal by a previous service instance"`, persisted (so a redelivery is answered the same way by rule c), published and acknowledged through `_finish`; one REJECT measurement with that detail as its outcome; `info("seat_run_abandoned", ...)`.
4. **Rule g — the worktree fence**, taken in `_run` after the environment is built and before the run is registered: `decision = self._fence.acquire(Path(request.cwd), self._holder(request))`.
   - `ACQUIRED` → the run goes ahead; the lock is released in the run's `finally`, after the result was persisted, published and acknowledged (and after a spawn failure).
   - `SUPERSEDED` → a `RunResult` with `status=SUPERSEDED`, `detail=f"superseded: attempt {attempt} is below the worktree's high-water mark"`, persisted, published and acknowledged through `_finish`; one REJECT measurement with that detail.
   - `BUSY_SUPERSEDING` → `_reject(..., f"worktree busy: superseding {decision.holder_run_id}")` (never persisted: the caller defers and retries the same run id after the holder releases, ADR-0046 §6). The fence has already written `stop` into the holder's inbox.
   - `BUSY` → `_reject(..., "worktree busy")`.
   The holder is `FenceHolder(run_id=request.run_id, key=<supersedes.key or None>, attempt=<supersedes.attempt or 0>, loop_id=self._loop_id.value, instance=self._instance, run_dir=<str(cwd / run_dir) or None>, started_at=now, deadline_at=now + timedelta(seconds=request.deadline_seconds))`.
5. The order of the checks in `handle` (the consumer callback) becomes: a (dead-letter), **b**, f (executor), c (persisted result), **d**, e (`start_by`), then `_run`: environment, **g**, h.

## Where to change
`src/vibey/infrastructure/loop_service/seat_host.py` only (plus the test file). It is longer than 100 lines: use `edit_file` only, never `write_file`. Each anchor below is text lane `loops-seat-host-core` wrote; if one is not found verbatim (formatting may have re-wrapped a long line), `read_file` the method and insert at the described point. Do not change any other line.
- **Imports.** Add `import json`, `from datetime import timedelta` (merge into the existing `from datetime import datetime`), `from pathlib import Path`, `from vibey.infrastructure.loop_service.interfaces.worktree_lock_interface import WorktreeFenceInterface` and `from vibey.infrastructure.loop_service.worktree_lock import FenceDecision, FenceHolder, FenceOutcome, WorktreeFence`. After the imports, add the module constant
  `TERMINAL_META_STATUSES: Final = frozenset({"finished", "failed", "stopped"})` (with `from typing import Final`).
- **Constructor parameter.** `old_string`:
  ```
          prefetch: int,
          logger: Logger | None = None,
      ) -> None:
  ```
  `new_string`: the same with `        fence: WorktreeFenceInterface | None = None,` inserted before the `logger` line.
- **Constructor body.** After the line `        self._log: Logger = logger if logger is not None else structlog.get_logger(__name__)` add:
  ```python
          self._fence: WorktreeFenceInterface = (
              fence
              if fence is not None
              else WorktreeFence(
                  stale_after=timedelta(seconds=config.stale_lock_seconds), clock=clock, logger=logger
              )
          )
  ```
- **Rule b.** `old_string`:
  ```
          request = message
          reason = self._executor.reason_to_reject(request)
  ```
  `new_string`:
  ```python
          request = message
          active = self._active.get(request.run_id)
          if active is not None:
              # Rule b: the broker redelivered a run this host is running (a channel blip).
              # Start nothing; the running run settles this delivery when it ends.
              active.delivery = delivery
              self._log.info("seat_run_rebound", seat=self._seat, run_id=str(request.run_id))
              return
          reason = self._executor.reason_to_reject(request)
  ```
- **Rule d.** `old_string`: `        if self._clock.now() > request.start_by:` ; `new_string`:
  ```python
          if self._left_non_terminal(request):
              await self._abandon(delivery, request)
              return
          if self._clock.now() > request.start_by:
  ```
- **Rule g.** `old_string`:
  ```
          started_at = self._clock.now()
          entry = _ActiveRun(request=request, delivery=delivery, started_at=started_at)
  ```
  `new_string`:
  ```python
          decision = self._fence.acquire(Path(request.cwd), self._holder(request))
          if decision.outcome is not FenceOutcome.ACQUIRED:
              await self._refuse(delivery, request, decision)
              return
          started_at = self._clock.now()
          entry = _ActiveRun(request=request, delivery=delivery, started_at=started_at)
  ```
- **Release.** `old_string`:
  ```
          finally:
              self._active.pop(request.run_id, None)
  ```
  `new_string`: the same plus the line `            self._fence.release(Path(request.cwd), request.run_id)`.
- **New private methods**, appended after the last line of `_environment_for` (`        return overlay`):
  ```python
      def _holder(self, request: RunRequest) -> FenceHolder:
          now = self._clock.now()
          supersedes = request.supersedes
          return FenceHolder(
              run_id=request.run_id,
              key=None if supersedes is None else supersedes.key,
              attempt=0 if supersedes is None else supersedes.attempt,
              loop_id=self._loop_id.value,
              instance=self._instance,
              run_dir=None if request.run_dir is None else str(Path(request.cwd) / request.run_dir),
              started_at=now,
              deadline_at=now + timedelta(seconds=request.deadline_seconds),
          )

      async def _refuse(
          self, delivery: AmqpDeliveryInterface, request: RunRequest, decision: FenceDecision
      ) -> None:
          if decision.outcome is FenceOutcome.SUPERSEDED:
              # Rule g: a higher attempt of this job already reached the worktree. Persisted,
              # so a redelivery of this attempt is answered the same way (rule c).
              attempt = 0 if request.supersedes is None else request.supersedes.attempt
              await self._answer_without_running(
                  delivery,
                  request,
                  RunStatus.SUPERSEDED,
                  f"superseded: attempt {attempt} is below the worktree's high-water mark",
              )
              return
          if decision.outcome is FenceOutcome.BUSY_SUPERSEDING:
              await self._reject(
                  delivery, request, f"worktree busy: superseding {decision.holder_run_id}"
              )
              return
          await self._reject(delivery, request, "worktree busy")

      def _left_non_terminal(self, request: RunRequest) -> bool:
          """Rule d: a run directory a previous instance started and never finished."""
          if request.run_dir is None:
              return False
          run_dir = Path(request.cwd) / request.run_dir
          if not run_dir.is_dir():
              return False
          try:
              raw = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
          except (OSError, ValueError):
              raw = None
          status = raw.get("status") if isinstance(raw, dict) else None
          return status not in TERMINAL_META_STATUSES

      async def _abandon(self, delivery: AmqpDeliveryInterface, request: RunRequest) -> None:
          await self._answer_without_running(
              delivery,
              request,
              RunStatus.ABANDONED,
              "run directory left non-terminal by a previous service instance",
          )

      async def _answer_without_running(
          self, delivery: AmqpDeliveryInterface, request: RunRequest, status: RunStatus, detail: str
      ) -> None:
          finished_at = self._clock.now()
          result = RunResult(
              run_id=request.run_id,
              status=status,
              exit_code=None,
              meta_status=None,
              started_at=None,
              finished_at=finished_at,
              detail=detail,
              stdout=None,
              stderr=None,
              cached_at=None,
          )
          await self._finish(delivery, request, result)
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
          self._log.info(
              "seat_run_answered_without_running",
              seat=self._seat,
              run_id=str(request.run_id),
              status=status.value,
          )
  ```
- Then `uv run ruff check --fix src/vibey/infrastructure/loop_service/seat_host.py tests/infrastructure/loop_service` and `uv run ruff format` on the same paths.
- **New** `tests/infrastructure/loop_service/test_seat_host_fence.py`. Line 1 is the provenance comment, copied byte for byte from line 1 of `src/vibey/infrastructure/process/reaper.py`.

## Acceptance criteria
- [ ] `tests/infrastructure/loop_service/test_seat_host_core.py` passes **unedited** (its runs now take and release the real fence in their `tmp_path` worktrees).
- [ ] A redelivered active run starts no second process, and the run's end settles the redelivered delivery.
- [ ] A lower attempt holding a worktree is stopped through its inbox even when the successor arrives on a seat host of the **other** loop.
- [ ] No lock is left behind after a normal run, a spawn failure or a deadline.
- [ ] No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`; `tests/meta/patching_baseline.json` does not change.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_seat_host_fence.py`. Copy the helpers `NOW`, `SEAT`, `MODEL`, `REPLIES`, `_Clock`, `_Rig`, `_request`, `_send` and `_replies` from `test_seat_host_core.py` (do not import across test modules), and give `_rig` two more keywords, `fence: WorktreeFenceInterface | None = None` and `amqp: InMemoryAmqpClient | None = None`, passed through to `SeatHost(..., fence=fence)`. Each test uses `tmp_path / "wt"` as the worktree. A background run is started with `task = asyncio.create_task(_send(rig, body))`, then awaited until it is running with `for _ in range(200): if rig.executor.runs: break; await asyncio.sleep(0.01)`.
- `test_a_redelivered_active_run_starts_nothing_and_its_end_settles_the_redelivery`: `FakeLocalRunExecutor(hang=True)`; start the run in the background; `await rig.amqp.close(); await rig.amqp.connect()` (the broker returns the unacknowledged delivery to the queue, as after a channel blip); `redelivery = await rig.amqp.get(seat_queue)` (its `delivery_count == 1`); `await rig.host.handle(redelivery)` returns at once. The in-memory broker pushes one delivery at a time per queue, so the test hands the redelivery to the host's public consumer callback itself. `len(rig.executor.starts) == 1`. Then `rig.executor.runs[0].finish(0)` and `await task`. The replies are exactly one `RunAccepted` and one `RunResult` (`EXITED`, 0), and `await redelivery.complete() is False` (the run's end already acknowledged the redelivery).
- `test_a_non_terminal_run_dir_is_abandoned_and_persisted`: `run_dir=".sovereignloop/runs/r1"`, created with `meta.json` holding `{"status": "running"}` → one reply, `ABANDONED`, detail `"run directory left non-terminal by a previous service instance"`; persisted; `rig.executor.starts == []`; the last measurement is `REJECT` with that outcome. The same for an existing run directory with no `meta.json`, and for one whose `meta.json` holds `["x"]`.
- `test_a_terminal_or_absent_run_dir_runs_normally`: `meta.json` holding `{"status": "finished"}` → the run starts and ends `EXITED`; a `run_dir` that does not exist → the same.
- `test_an_attempt_below_the_high_water_is_superseded_and_persisted`: `(cwd / ".vibey").mkdir(parents=True)`, `(cwd / ".vibey" / "supersede.json").write_text('{"job-1": 2}')`; a request with `supersedes=RunSupersede(key="job-1", attempt=1)` → `SUPERSEDED`, detail `"superseded: attempt 1 is below the worktree's high-water mark"`, persisted, not started, a REJECT measurement; sending it again re-sends the same persisted result.
- `test_a_lower_attempt_is_stopped_across_loops_and_the_successor_rejected`: rig A (sovereignloop, seat `SEAT`, `FakeLocalRunExecutor(hang=True)`) runs attempt 0 of `"job-1"` with `run_dir=".sovereignloop/runs/r0"` in the background. Rig B (paidloop, seat `"claudeloop"`, `model=None`, its own `InMemoryAmqpClient`) receives attempt 1 of `"job-1"` (`loop_id=PAIDLOOP`, `engine_id="claudeloop"`) on the **same** `cwd` → `REJECTED` with detail `f"worktree busy: superseding {run0_id}"`, not persisted; exactly one `inbox/*-stop.json` under `cwd / ".sovereignloop/runs/r0"`. Finish rig A's run and await its task.
- `test_another_key_on_a_busy_worktree_is_rejected`: while attempt 0 of `"job-1"` runs in the background, a request of `"job-2"` on a second rig with the same `cwd` → `REJECTED`, detail `"worktree busy"`; a request with no `supersedes` → the same.
- `test_the_lock_is_released_after_every_ending`: after a normal run, after a spawn failure (`start_error=OSError("gone")`) and after a deadline (`hang=True`, `deadline_seconds=1`), `(cwd / ".vibey" / "run.lock").exists() is False`.
- `test_an_injected_fence_is_used`: `fence=InMemoryWorktreeFence()`: after a run with `supersedes=RunSupersede(key="job-1", attempt=3)`, `fence.holders == {}` and `fence.high_water(Path(request.cwd), "job-1") == 3`; `(cwd / ".vibey" / "run.lock").exists() is False` and `(cwd / ".vibey" / "supersede.json").exists() is False` (the injected fence was used, not the file fence).

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
git diff --stat HEAD~1 -- tests/infrastructure/loop_service/test_seat_host_core.py
```
Nothing here is OS-specific beyond the fence's POSIX calls, which behave alike on Arch Linux and macOS (8.h).

## Out of scope
- Progress, `busy`, `control`, `stop_lower_attempts`, the run-finished callback and the drain (lane `loops-seat-host-drain`).
- The `SUPERSEDE` control broadcast (lane `loops-control-and-dead-letters`).
- The fence itself (lane `loops-worktree-fence`, landed).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Protected tests are never edited.
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject. Follow `STORM/EDITING-RULES.md`.

**Depends on:** `loops-seat-host-core`, `loops-worktree-fence`
- `loops-seat-host-core`: `seat_host.py`, the text this lane anchors on (and, through it, the default-exchange precondition of `surfaces-amqp-publish-modes`).
- `loops-worktree-fence`: `WorktreeFence`, `FenceHolder`, `FenceOutcome`, `FenceDecision` and `InMemoryWorktreeFence`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
