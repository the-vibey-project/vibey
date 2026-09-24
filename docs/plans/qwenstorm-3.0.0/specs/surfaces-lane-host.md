## Title
feat(surfaces): SurfaceLaneHost runs one surface's single lane — lease or standby, consume both queues, reconcile, measure, exit on lease loss, drain on stop

## Why
Draft ADR-0047 §1 (`specs/ADR-surface-lanes.md`) makes a surface lane "the one consumer
instance that performs every operation vibey makes on one surface" (sub-doctrine 8.f, "a single
lane per deployment"):

- **A broker lease.** "A lane first declares an exclusive, auto-delete queue named
  `<prefix>.surface.<name>.lock` … The holder is the instance. A second process that is started
  stays a **standby**: it polls for the lease and consumes nothing."
- **When the connection is lost, the lane exits.** "It does not try to reclaim its lease. The
  supervisor restarts it" — 8.c's "a restart, never a second copy".
- **Capacity inside the instance is a key.** "Reads run concurrently up to `read_prefetch` …
  The write queue is consumed with prefetch 1, because FIFO order of writes is what makes
  replaying an overwrite safe (§8)."
- **The park** runs every `reconcile_interval_seconds` (§9), and every interval the lane
  measures itself (8.g, lane `surfaces-lane-meter`).

The per-delivery work is `surfaces-dispatcher`'s; this lane is the lifecycle around it. ADR-0047
lane S23. "The lane owns the surface's credentials and its sovereign adapter, and nothing else in
vibey talks to that surface" — the composition (`surfaces-composition`) makes that true.

## Required behaviour
In the new `src/vibey/infrastructure/surface_lanes/host.py`:

1. `LANE_EXIT_OK: Final = 0`, `LANE_EXIT_LEASE_LOST: Final = 3`.
2. `class SurfaceLaneHost`,
   `__init__(self, *, surface: SurfaceName, client: AmqpClientInterface, leases: AmqpLeasesInterface, topology: SurfaceLaneTopologyInterface, names: SurfaceQueueNamesInterface, dispatcher: SurfaceRequestDispatcherInterface, reconciler: SurfaceDeadLetterReconcilerInterface, meter: SurfaceLaneMeterInterface, settings: SurfacesConfigInterface, logger: Logger, backend: str, instance: str, cache: CacheLaneHandlerInterface | None = None, sleep: Callable[[float], Awaitable[None]] = asyncio.sleep)`.
3. `async run(self, stop: asyncio.Event) -> int`:
   1. **Lease or standby.** `lease = await leases.acquire_exclusive(names.lock_queue(surface))`.
      While it is `None` and `stop` is not set: log `surface.lane.standby` at `info` once (with
      `surface`, `instance`), `await sleep(settings.standby_poll_seconds)`, try again. If `stop`
      is set first, return `LANE_EXIT_OK` having consumed nothing.
   2. `await topology.declare(surface)`; log `surface.lane.started` at `info` with `surface`,
      `instance`, `backend` (for example `PlaneTrackerAdapter` or `InMemoryTracker`: "A lane whose
      surface has no credentials serves the in-memory adapter, and says so at start", §2) and
      `read_prefetch`.
   3. Consume `names.write_queue(surface)` with `prefetch=1` and `names.read_queue(surface)`
      with `prefetch=settings.read_prefetch`. Each consumer handler starts
      `asyncio.create_task(dispatcher.handle(delivery))` and keeps the task in a set until it
      finishes, so reads run concurrently and the write queue stays FIFO (prefetch 1 means the
      next write is pushed only after the previous one settles).
   4. Loop until one of these happens, whichever is first:
      - `stop` is set → go to 5;
      - `lease.wait_lost()` returns → log `surface.lane.lease_lost` at `error` (naming 8.c: the
        supervisor restarts the lane; it never reclaims), cancel both consumers, and return
        `LANE_EXIT_LEASE_LOST` without waiting for in-flight work;
      - `settings.reconcile_interval_seconds` elapses (through `sleep`) → `await reconciler.drain()`
        and `await meter.flush(client, {"write": …, "read": …, "dead": …}, cache)`; an exception
        from either is logged `surface.lane.tick_failed` and the loop continues.
   5. **Drain on stop.** Cancel both consumers (take nothing new); wait for the in-flight tasks
      for at most `settings.drain_grace_seconds`; unfinished tasks are left to the broker (their
      deliveries are unsettled and will be redelivered to the next instance) and counted in the
      log. Run one last `reconciler.drain()` and `meter.flush(...)`, `await lease.release()`,
      log `surface.lane.stopped` with `in_flight_left`, and return `LANE_EXIT_OK`.
4. **Interface** `surface_lanes/interfaces/host_interface.py`:
   `@runtime_checkable class SurfaceLaneHostInterface(Protocol)` with `run`; exported. Registry:
   the real host over `InMemoryAmqpClient`, `InMemoryAmqpLeases` and the in-memory parts (a
   `functools.partial`), in `REGISTRY` and `DRIVER_SEAMS`.

## Where to change
- New `src/vibey/infrastructure/surface_lanes/host.py`,
  `src/vibey/infrastructure/surface_lanes/interfaces/host_interface.py`; interfaces
  `__init__.py`; `tests/fakes/registry.py`.
- New `tests/infrastructure/surface_lanes/test_host.py`.

## Acceptance criteria
- [ ] Two hosts for one surface sharing one `InMemoryAmqpLeases`: the first consumes; the second logs `surface.lane.standby` and consumes nothing; when the first stops and releases, the second takes the lease and starts.
- [ ] A request published through a real `SurfaceLaneClient` to a running host is answered (end to end over `memory_amqp` with in-memory adapters).
- [ ] 32 concurrent cache reads are in flight at once (a blocking cache port class in the test proves concurrency up to `read_prefetch`), while two writes run strictly one after the other.
- [ ] `simulate_loss()` on the lease makes `run` return 3 promptly and consume nothing more.
- [ ] Setting `stop` returns 0 after in-flight work finishes, releases the lease, and a task that outlives `drain_grace_seconds=1` is reported, not awaited forever.
- [ ] A reconcile tick drains the dead queue and logs `surface.lane.measured`; a failing tick is logged and the loop continues.
- [ ] The start line names the backend.
- [ ] 100% `infrastructure/` branch coverage; no test sleeps in real time for more than 2 s in total (drive the ticks with an injected sleep).

## Tests to write first (TDD)
`tests/infrastructure/surface_lanes/test_host.py` (no service; `memory_amqp`, `InMemoryAmqpLeases`, in-memory adapters and stores, `RecordingLogger`, `FakeClock`, a controllable sleep class in the module):
- `test_the_second_host_is_a_standby_until_the_lease_frees`
- `test_a_request_is_answered_end_to_end`
- `test_reads_are_concurrent_and_writes_are_fifo`
- `test_losing_the_lease_exits_three`
- `test_stop_drains_in_flight_work_and_releases`
- `test_the_drain_is_bounded_by_the_grace`
- `test_each_tick_reconciles_and_measures`
- `test_a_failing_tick_does_not_stop_the_lane`
- `test_the_start_line_names_the_backend`
- `test_host_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/surface_lanes tests/fakes
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Building a host from configuration (`surfaces-composition`) and the `vibey surface serve`
  command (`surfaces-cli-serve-ping`). The family `AmqpServiceHost` the ADR names as a follow-up
  (§16). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees
  (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the Title
  as the subject.

## Lane card
- **Depends on:** `surfaces-dispatcher`, `surfaces-reconcile`, `surfaces-amqp-lease-memory`, `surfaces-amqp-queue-limits` (single active consumer in memory).
- **Shares a file with:** `tests/fakes/registry.py`.
- **Must keep passing unchanged:** everything under `tests/infrastructure/surface_lanes/`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol in `surface_lanes/interfaces/`.
  - Substitute only at a declared seam; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no service.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
