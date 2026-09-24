## Title
feat(loop-service): LoopServiceProcess runs a router, its dead-letter/control/probe consumers and (in --role all) the resident schedule together

ADR-0046 lane L62 (slug `loops-service-process`).

## Why
Draft ADR-0046 §10's file table
(`STORM/specs/ADR-two-loops.md:304`) lists `router.py`,
`seat_host.py`, `resident_schedule.py`, `control.py` as siblings inside
`infrastructure/loop_service/`, but nothing yet turns them into one runnable process.
`loops-router-routing`'s own Why cites "decision D5: all three [forwarding, dead letters, probes]
run in the router's process." `loops-resident-schedule`'s own Why cites "decision D6: residency
switching runs only in `vibey loop-service --role all`, where one process hosts several sovereign
seats; in `--role seat` each host consumes its own seat." §11 (`:314-323`) describes the chart's
shape this process must support: "Each loop renders one **router** Deployment, and one **seat-host**
Deployment per model it declares" -- so a `--role router` process runs only the router plus its
control/dead-letter/probe consumers (no seat hosts, no resident schedule), a `--role seat` process
runs exactly one `SeatHost` for one seat (no router, no schedule), and `--role all` (the default,
what a single-machine install runs) runs everything in one process, which is also the only role
where the resident schedule makes sense (switching *between* seats requires holding more than
one in the same process). §11 also fixes `replicas: 1` for every one of these Deployments (8.c),
so this class never spawns a second instance of anything; it is a **within-process** orchestrator
of already-built pieces, not a supervisor of other OS processes.

## Required behaviour
All in `src/vibey/infrastructure/loop_service/service_process.py`.
1. **`class LoopServiceRole(StrEnum)`**: `ALL = "all"`, `ROUTER = "router"`, `SEAT = "seat"`.
   (A domain-shaped enum kept in infrastructure, not `domain/`, because it names a *deployment*
   concept the CLI and the chart share, not a fact about the loop's own protocol; if `domain/loop.py`
   already declares an equivalent enum by this point, **stop and report** rather than declaring a
   second one -- 10.e.)
2. **`class LoopServiceProcess`**, built as
   `LoopServiceProcess(*, role: LoopServiceRole, router: LoopRouterInterface | None,
   dead_letters: DeadLetterReplierInterface | None, control: ControlConsumerInterface | None,
   probes: ProbeConsumerInterface | None, scheduler: ResidentSeatSchedulerInterface | None, seats:
   Mapping[str, SeatHostInterface], logger: Logger | None = None)`. The constructor enforces the
   role/component pairing so a caller can never build an internally inconsistent process:
   - `ALL`: every one of `router`, `dead_letters`, `control`, `probes`, `scheduler` must be
     given, and `seats` non-empty; else `ValueError("--role all needs a router, its
     control/dead-letter/probe consumers, a resident schedule and at least one seat")`.
   - `ROUTER`: `router`, `dead_letters`, `control`, `probes` must be given, `scheduler` and
     `seats` must both be **absent** (`None` / empty); else `ValueError("--role router needs a
     router and its control/dead-letter/probe consumers, and no seat or scheduler")`.
   - `SEAT`: `seats` must hold exactly one entry, and `router`, `dead_letters`, `control`,
     `probes`, `scheduler` must all be `None`; else `ValueError("--role seat needs exactly one
     seat host, and no router, scheduler or control consumer")`.
3. **`async def start(self) -> None`**, in this order, each step only when that component is
   present for the role:
   1. every seat host's `declare()` (idempotent, safe to call whether or not this process also
      consumes it yet);
   2. the router's `start()` (declares the whole topology, including every seat queue, so a
      `--role seat` process that starts *before* any router has run still finds its queue
      correctly declared -- `SeatHost.declare()` in step 1 already covers a seat process running
      alone, and the router's own `declare_queue` calls are idempotent redeclares when both race);
   3. for `ALL`: `await self._scheduler.start()` (which itself calls `consume()` on exactly the
      resident seat, per `loops-resident-schedule`'s own `start` -- **this process must not also
      call `consume()` on any seat host directly in this role**, since the scheduler owns that
      decision for `ALL`);
   4. for `SEAT`: the process's one seat host's own `consume()` (there is no scheduler to decide
      residency in this role: a `--role seat` process always consumes its one seat, unconditionally
      -- residency switching is meaningless when a process holds only one seat);
   5. `dead_letters.start()`, `control.start()`, `probes.start()` (router-hosted roles only).
   `self._log.info("loop_service_started", role=self._role.value, seats=list(self._seats))`.
4. **`async def run_forever(self) -> None`**: for `ALL`, `await self._scheduler.run_forever()`
   (which ticks on its own configured interval until `stop()`, per `loops-resident-schedule`);
   for `ROUTER` and `SEAT`, `await self._stopping.wait()` (an `asyncio.Event` this class owns,
   set by `stop()`) -- there is nothing periodic to tick in those roles, so this coroutine simply
   blocks until told to end.
5. **`async def stop(self, grace_seconds: float) -> None`** -- the drain, in the reverse order of
   `start`:
   1. for `ALL`: `await self._scheduler.stop()`;
   2. `probes.stop()`, `control.stop()`, `dead_letters.stop()` (router-hosted roles only);
   3. `router.stop()` (`ROUTER` and `ALL`);
   4. every seat host's own `stop(grace_seconds)` (its own drain, lane `loops-seat-host-drain`) --
      for `ALL`, every seat in `self._seats`, not only the currently-resident one: a switch may
      have left a non-resident host mid-cancel, and draining is idempotent on an already-cancelled
      host;
   5. `self._stopping.set()` (releases `run_forever` for `ROUTER`/`SEAT`);
   `self._log.info("loop_service_stopped", role=self._role.value)`.
6. **`src/vibey/infrastructure/loop_service/interfaces/service_process_interface.py`** (new):
   `@runtime_checkable class LoopServiceProcessInterface(Protocol)` with `async start(self) ->
   None`, `async run_forever(self) -> None`, `async stop(self, grace_seconds: float) -> None`.
7. **Fake**, appended to `tests/fakes/loops.py`:
   ```python
   class FakeLoopServiceProcess:
       """LoopServiceProcessInterface in memory: records its lifecycle calls."""

       def __init__(self) -> None:
           self.calls: list[str] = []
           self._stopping = asyncio.Event()

       async def start(self) -> None:
           self.calls.append("start")

       async def run_forever(self) -> None:
           self.calls.append("run_forever")
           await self._stopping.wait()

       async def stop(self, grace_seconds: float) -> None:
           self.calls.append(f"stop:{grace_seconds}")
           self._stopping.set()
   ```
8. **Registry**: `LoopServiceProcessInterface` is appended to `DRIVER_SEAMS`; `REGISTRY` gains
   `FakeRegistration(port=LoopServiceProcessInterface, build=FakeLoopServiceProcess)`.

## Where to change
Line 1 of every new file is the provenance comment, copied byte for byte from line 1 of
`src/vibey/infrastructure/process/reaper.py`.
- **New** `src/vibey/infrastructure/loop_service/service_process.py` (behaviours 1-5). Imports:
  `asyncio`, `from collections.abc import Mapping`, `from enum import StrEnum`, `structlog`,
  `from vibey.application.interfaces import Logger`,
  `from vibey.infrastructure.loop_service.interfaces.control_interface import
  ControlConsumerInterface, DeadLetterReplierInterface`,
  `from vibey.infrastructure.loop_service.interfaces.probe_consumer_interface import
  ProbeConsumerInterface`, `from vibey.infrastructure.loop_service.interfaces.resident_schedule_interface
  import ResidentSeatSchedulerInterface`, `from vibey.infrastructure.loop_service.interfaces.router_interface
  import LoopRouterInterface`, `from vibey.infrastructure.loop_service.interfaces.seat_host_interface
  import SeatHostInterface`. `__all__ = ["LoopServiceProcess", "LoopServiceRole"]`. Module
  docstring: ADR-0046 §11's three deployment roles; decisions D5 and D6 for what runs together.
- **First**, `grep -rn "class.*Role" src/vibey/domain/loop.py` to confirm no role enum already
  exists there; if one does, import and reuse it instead of declaring `LoopServiceRole` here, and
  say so in the commit body.
- **New** `src/vibey/infrastructure/loop_service/interfaces/service_process_interface.py`
  (behaviour 6).
- **`tests/fakes/loops.py`**: append the class of behaviour 7 with `edit_file` (add `import
  asyncio` to its imports if missing).
- **`tests/fakes/registry.py`**: run the registration script of lane `loops-result-store` (the
  `register_fakes.py` block) with only these lists, then delete the script:
  ```python
  IMPORTS = [
      "from tests.fakes.loops import FakeLoopServiceProcess",
      "from vibey.infrastructure.loop_service.interfaces.service_process_interface import LoopServiceProcessInterface",
  ]
  SEAMS = ["LoopServiceProcessInterface"]
  ENTRIES = ["FakeRegistration(port=LoopServiceProcessInterface, build=FakeLoopServiceProcess)"]
  ```
- Then `uv run ruff check --fix` and `uv run ruff format` on
  `src/vibey/infrastructure/loop_service tests/fakes/loops.py tests/fakes/registry.py
  tests/infrastructure/loop_service`.
- **New** `tests/infrastructure/loop_service/test_service_process.py`.

## Acceptance criteria
- [ ] Building a process for a role without the components that role requires raises `ValueError`
      naming the missing set, for all three roles.
- [ ] `--role all`'s `start` never calls `consume()` on any seat host directly; only the scheduler
      does.
- [ ] `--role seat`'s `start` always consumes its one seat, with no scheduler involved.
- [ ] `stop` drains every component in the reverse order it started, and releases `run_forever`.
- [ ] No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`; `tests/meta/patching_baseline.json`
      does not change; `tests/fakes/test_port_parity.py` passes.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_service_process.py`. Use `FakeSeatHost`,
`FakeResidentScheduler`, `FakeLoopRouter`, `FakeDeadLetterReplier`, `FakeControlConsumer`,
`FakeProbeConsumer` (all from `tests.fakes.loops`).
- `test_all_role_requires_every_component`: omitting any one of `router`, `dead_letters`,
  `control`, `probes`, `scheduler`, or passing empty `seats`, each raises `ValueError` with the
  behaviour-2 message for `ALL`.
- `test_router_role_forbids_a_scheduler_or_seats`: `router`+its three consumers with a non-empty
  `seats` or a `scheduler` set raises; with both absent, it constructs.
- `test_seat_role_requires_exactly_one_seat_and_nothing_else`: two seats, or one seat plus a
  `router`, each raises; one seat alone constructs.
- `test_all_role_start_lets_the_scheduler_consume_not_the_process`: after `start()`, the resident
  `FakeSeatHost`'s `calls` include `"consume"` **only** because `FakeResidentScheduler.start()`
  itself would call it in the real class -- assert instead that the process's own `start` never
  calls `.consume()` on any host directly (spy via a `FakeSeatHost` subclass that raises if
  `consume` is called from outside the scheduler double, or simpler: assert `scheduler.started is
  True` and that no host's `calls` contains `"consume"` when the scheduler is the fake, which
  never touches real hosts).
- `test_seat_role_start_consumes_its_one_seat`: after `start()`, the one seat host's `calls ==
  ["declare", "consume"]`.
- `test_router_role_start_and_stop_the_three_consumers`: after `start()`, `dead_letters.started`,
  `control.started`, `probes.started` are all `True`; after `stop(5.0)`, all `False` and
  `router.stopped is True`.
- `test_run_forever_blocks_until_stop_for_router_and_seat_roles`: for `ROUTER`, `task =
  asyncio.create_task(process.run_forever())`; it is not done after a short sleep; `await
  process.stop(1.0)`; `await task` completes promptly.
- `test_all_role_run_forever_delegates_to_the_scheduler`: `run_forever()` awaits
  `scheduler.run_forever()` (the fake's own `_stopping` event); `stop()` calls
  `scheduler.stop()` first.
- `test_stop_drains_every_seat_for_all_role_not_only_the_resident_one`: two seats in `ALL`; after
  `stop(2.0)`, both hosts' `calls` include `"cancel"`... wait, `FakeSeatHost` has no async `stop`
  in this ADR's own fake (lane `loops-seat-host-drain` gave it one): use that fake's `stops` list
  instead -- both hosts' `stops == [2.0]`.
- `test_the_process_and_its_fake_satisfy_the_interface`: `isinstance` of a real
  `LoopServiceProcess` and of `FakeLoopServiceProcess()` against `LoopServiceProcessInterface`.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/fakes tests/meta/test_patching_ratchet.py
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
git status --short
```

## Out of scope
- Building the real router, seat hosts, resident schedule and consumers this process wraps (their
  own lanes, all landed).
- Reading `[loop_services]` / CLI flags to decide which components to build (lane
  `loops-bootstrap-loop-service`); the `vibey loop-service` CLI command itself (lane
  `loops-cli-loop-service`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Protected tests
  are never edited.
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject. Follow
  `EDITING-RULES.md`.

**Depends on:** `loops-router-forwarding`, `loops-probe-consumer`, `loops-control-and-dead-letters`, `loops-resident-schedule`.

## Hard repository rules (always)
- `domain/` stays pure: no I/O, no async, no clock, no network. Enforced by `tests/domain/test_domain_purity.py`, which walks the AST.
- Dependencies point inward only: `domain -> application -> infrastructure -> cli`, enforced by `import-linter` (`uv run lint-imports`).
- `CreditsExhausted` never has a `resets_at` field. A capacity rejection always outranks a completion claim.
- Code lives in classes, and every class gets an interface declared beside it (ADR-0016, sub-doctrine 9.b): `pkg/x.py` implies `pkg/interfaces/x_interface.py` (or an entry in an existing `interfaces/` module in the same package). A module-level function is the method of last resort, and needs a written reason at its definition. Interfaces declare; they never consume, and no Protocol is declared outside a package named `interfaces`.
- Every job is idempotent under replay; the ledger is append-only (no updates, no deletes; a correction is a new event that supersedes the prior one).
- `write_file` REPLACES the whole file. Never use it on a file that already exists unless the complete content with the change applied is written back. Every line not meant to change must still be there. For any existing file longer than 100 lines, do not use `write_file` at all.
- Change an existing file with the `edit_file` tool: `path`, an `old_string` copied exactly from `read_file` output (enough lines to be unique), and the `new_string`. It replaces one occurrence and reports when the text is missing or not unique. Only if `edit_file` cannot express a change, use a checked replacement through the `shell` tool, and the `shell` tool takes an **argv list**, never a shell string: a shell here-document that redirects a block of text into a command never works this way and must never be written. For any one-off script, write it with `write_file` to `.qwenstorm/<name>.py`, then run it as `["python3", ".qwenstorm/<name>.py"]`. To append to an existing file, use `edit_file` with `old_string` equal to the file's exact last few lines. Copy `old_string` exactly, including indentation; if a checked assert fails, read the file again and fix the string; never fall back to rewriting the whole file.
- Add tests by appending to an existing test file (read it, append, write the whole file back with everything before the addition unchanged) or by creating a new test file. Never rewrite an existing test file's prior content.
- Every source file begins with the provenance header line `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`. Keep it on every file touched, and put it on every file created (copy it from a neighbour file in the same package, byte for byte).
- Only edit the files named under "Where to change" and the tests named under "Tests to write first". If another file seems like it must change, say so in the verdict instead of editing it.
- After each change, run the focused tests named in this spec. If a test not meant to be affected fails, undo the change with a targeted replacement and try again rather than pushing forward.
- Before the final verdict, run `git diff --stat` and confirm no file lost lines that were not meant to be removed.
- Tests substitute only at declared seams: constructor injection, keyword injection, or a named fixture. Never `monkeypatch.setattr` on an import, a module attribute or a class attribute; never `mock.patch`; never a bare `MagicMock` or `AsyncMock` standing in for a port. A fake is a plain class with real in-memory behaviour for every method it implements; no method body is only `...`, only `pass`, only `return None`, or only `raise NotImplementedError`.
- Persistence goes only through the ORM seams declared in the `orm-*.md` specs in this same directory. No raw `asyncpg` SQL, no `text()`, no `exec_driver_sql()` and no SQL string literal in a loops lane.
- No failure-text string a lane writes may trail off with an ellipsis character: write every failure message out in full, to its last word.
- Do not edit `CHANGELOG.md`, anything under `docs/`, any ADR, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` or a skill tree (the docs wave owns those). Do not push, open a pull request, or change a git remote. Commit locally, with the Title as the Conventional Commit subject.
- Protected tests are never edited, under any circumstance: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`. They must keep passing.
