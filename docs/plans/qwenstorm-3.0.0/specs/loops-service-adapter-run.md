## Title
feat(loop-service): ServiceEngineAdapter starts and tails a run over the bus instead of a local process

ADR-0046 lane L57a (slug `loops-service-adapter-run`).

## Why
Draft ADR-0046 §3, "Flow for a BUILD job" (`STORM/specs/ADR-two-loops.md:169-179`),
step 4: "It returns an adapter bound to that engine" -- "Because of this order, `EngineAdapter.descriptor`
is known before `start`, exactly as `build_implement_handler.py:185` needs today." §10
(`:304`) places `infrastructure/loop_service/adapter.py` beside `client.py`. Lane
`loops-routing-ports` already declared the seam this lane fills:
`RoutedAdapterBinderInterface.bind(routed: RunRouted, *, job: JobRecord) -> EngineAdapter`, whose
job is to hand `build_implement_handler.py` an object satisfying the **existing**
`application/interfaces/engines.py::EngineAdapter` Protocol -- the same Protocol
`LoopProcessAdapter` (subprocess mode) already satisfies -- so that nothing downstream of
selection can tell whether a job ran locally or through a loop. §5's saturation row
(`:232`): "no `RunAccepted` by `start_by` … `EngineQueueSaturated`" is this adapter's own
`start()`, using the exact exception `loops-queue-saturated` defines. §10's file list also keeps
`RunDirTailer`, `RunInbox` and `StopSummaryReader` (`split-367-1-run-dir`) as the shared
machinery: "The inbox and tailer are R20's extracted classes" -- because the actual process a
seat host spawns still writes `events.jsonl`, `meta.json` and `stop-summary.md` onto the **shared
worktrees volume**, the same files `LoopProcessAdapter` tails today; only *who spawns the
process* changes, never where its evidence lands.

## Required behaviour
All in `src/vibey/infrastructure/loop_service/adapter.py`.
1. **First, read the exact seam.** `grep -n "class EngineAdapter" -A 40
   src/vibey/application/interfaces/engines.py` and `grep -n "class RunHandle" -A 15
   src/vibey/application/dto.py`. `ServiceEngineAdapter` must implement **every** method
   `EngineAdapter` declares, with identical signatures, and must return a `RunHandle` built with
   exactly the fields that dataclass declares. Everywhere this spec names a method or field of
   either that does not match what `grep` finds, follow what is actually declared, not this text,
   and say so in the commit body.
2. **`class ServiceEngineAdapter`**, built as
   `ServiceEngineAdapter(*, descriptor: EngineDescriptor, engine_id: EngineId, seat: str, model:
   str | None, route_id: UUID | None, loop_id: LoopId, client: LoopClientInterface, config:
   LoopConfigInterface, clock: Clock, caller: str, logger: Logger | None = None)`.
   - `descriptor` is a read-only property (matches `EngineAdapter.descriptor`, known before
     `start` per the ADR's own quoted requirement).
   - It keeps `self._active: dict[UUID, _ActiveServiceRun]` (a small private dataclass: `task:
     asyncio.Task[RunResult]`, `run_dir: Path`, `exit_code: int | None = None`).
3. **`async def start(self, spec: RunSpec) -> RunHandle`**:
   - Build `args = build_argv(self.descriptor, spec)` (the existing family function that already
     turns a descriptor's effort projection and a `RunSpec` into subprocess argv, proven by
     `tests/infrastructure/engines/test_argv.py`; reused here unchanged rather than re-derived --
     10.e).
   - Compute `run_dir_relative = f"{self.descriptor.state_dir}/runs/{spec.run_id}"` and
     `cwd = str(spec.worktree_path)`.
   - Build
     ```python
     request = RunRequest(
         run_id=spec.run_id,
         loop_id=self._loop_id,
         engine_id=self._engine_id.value,
         route_id=self._route_id,
         model_pin=self._model,
         purpose=RunPurpose.RUN,
         args=args,
         cwd=cwd,
         run_dir=run_dir_relative,
         supersedes=(
             None if spec.supersede_key is None
             else RunSupersede(key=spec.supersede_key, attempt=spec.attempt)
         ),
         deadline_seconds=self._config.run_deadline_seconds,
         start_by=self._clock.now() + timedelta(seconds=self._config.run_queue_wait_seconds),
         capture_output=False,
         requested_at=self._clock.now(),
         caller=self._caller,
     )
     ```
   - `accepted_holder: list[RunAccepted] = []`
     ```python
     task = asyncio.create_task(self._run(request, accepted_holder))
     deadline = asyncio.get_running_loop().time() + self._config.run_queue_wait_seconds
     while not accepted_holder and not task.done():
         if asyncio.get_running_loop().time() > deadline:
             task.cancel()
             raise EngineQueueSaturated(
                 self._clock.now() + timedelta(seconds=self._config.run_queue_wait_seconds),
                 f"no {self._loop_id.value} seat accepted run {spec.run_id} within "
                 f"{self._config.run_queue_wait_seconds}s",
             )
         await asyncio.sleep(0.02)
     if task.done() and task.exception() is not None:
         raise task.exception()  # a saturation raised inside _run, re-raised here
     accepted = accepted_holder[0]
     run_dir = spec.worktree_path / run_dir_relative
     self._active[spec.run_id] = _ActiveServiceRun(task=task, run_dir=run_dir)
     return RunHandle(run_id=spec.run_id, pid=accepted.pid, run_dir=run_dir, worktree_path=spec.worktree_path)
     ```
     (Adjust the final `RunHandle(...)` call to the exact field set `grep` found in step 1;
     `run_id`, `pid`, `run_dir` and `worktree_path` are the ones every existing adapter is known
     to fill, from `split-367-2-process-launcher`'s own test of `handle.pid`.)
   - `async def _run(self, request: RunRequest, accepted_holder: list[RunAccepted]) -> RunResult`
     drives the actual conversation on `self._client`, using a lower-level entry point than
     `submit_and_wait` so that acceptance and the terminal result are observable separately (if
     `LoopClient` (lane `loops-client`) exposes only `submit_and_wait`, call it with a callback
     that appends the accepted-equivalent information the moment progress or the result first
     proves acceptance happened -- concretely: read `loops-client`'s actual public surface first
     with `grep -n "async def" src/vibey/infrastructure/loop_service/client.py`, and if it has no
     way to observe `RunAccepted` before the terminal result, add exactly one keyword,
     `on_accepted: Callable[[RunAccepted], None] | None = None`, to `LoopClient.submit_and_wait`
     via a **small, additive** edit to that lane's file (never removing or renaming anything
     `loops-client`'s own tests assert), and call it with `on_accepted=lambda a:
     accepted_holder.append(a)`). Store the eventual `RunResult` on
     `self._active[request.run_id].result` and set `.exit_code` from it (`result.exit_code`, or
     `None` for a status that never carries one).
4. **`async def tail(self, handle: RunHandle) -> AsyncIterator[EngineEvent]`**: identical in
   spirit to `LoopProcessAdapter.tail` (lane `split-367-1-run-dir` extracted the reusable half):
   ```python
   tailer = RunDirTailer(self.descriptor)
   async for event in tailer.tail(
       handle.run_dir, run_id=handle.run_id, process_exit_code=lambda: self._exit_code(handle.run_id)
   ):
       yield event
   ```
   `_exit_code(self, run_id: UUID) -> int | None` returns `self._active[run_id].exit_code if
   run_id in self._active else None` -- `None` while the remote run is still going, so the tailer
   keeps polling `events.jsonl` on the shared volume exactly as it would for a local process,
   until the background task's `RunResult` arrives and sets a real exit code (or the tailer's own
   "process exited without terminal status" grace fires against a code that never really was a
   process exit code but a run status -- acceptable, because that grace path is intended purely
   as a bound on how long the tailer waits after it independently learns the run is done).
5. **`async def release_diagnostics(self, handle: RunHandle) -> None`** (if the grep of step 1
   shows this on `EngineAdapter`): pops `self._active.pop(handle.run_id, None)`; no diagnostic
   files to clean up locally (there is no local subprocess), so this is strictly bookkeeping.
6. **`RoutedAdapterBinder`**, implementing `RoutedAdapterBinderInterface` (lane
   `loops-routing-ports`):
   ```python
   class RoutedAdapterBinder:
       def __init__(
           self, *, client: LoopClientInterface, config: LoopConfigInterface, clock: Clock,
           descriptors: Mapping[EngineId, EngineDescriptor], caller: str,
       ) -> None:
           self._client = client
           self._config = config
           self._clock = clock
           self._descriptors = descriptors
           self._caller = caller

       def bind(self, routed: RunRouted, *, job: JobRecord) -> EngineAdapter:
           engine_id = ENGINE_ID_PARSER.known(routed.engine_id or "")
           if engine_id is None or engine_id not in self._descriptors:
               raise ValueError(f"routed engine {routed.engine_id} has no configured descriptor")
           return ServiceEngineAdapter(
               descriptor=self._descriptors[engine_id], engine_id=engine_id, seat=routed.seat or "",
               model=routed.model, route_id=routed.route_id, loop_id=routed.loop_id,
               client=self._client, config=self._config, clock=self._clock, caller=self._caller,
           )
   ```
   (`ValueError` here is a programming-error guard, not a user-facing path: `SelectingLoopProvider`
   already checks `routed.engine_id` is in its pool before calling `bind`, per that lane's own
   spec, so this only fires if a caller skips that check.)

## Where to change
Line 1 of every new file is the provenance comment, copied byte for byte from line 1 of
`src/vibey/infrastructure/engines/loop_process_adapter.py`.
- **Preconditions.** Run every `grep` of behaviour 1 and step 3's `grep -n "async def"
  src/vibey/infrastructure/loop_service/client.py` before writing anything; adjust field and
  method names to match what is actually declared, and note every adjustment in the commit body.
  `grep -n "def build_argv" src/vibey/infrastructure/engines/*.py` must find the existing argv
  builder; if it does not exist under that name, stop and report rather than re-deriving argv
  from a descriptor's `effort_projection` by hand.
- **New** `src/vibey/infrastructure/loop_service/adapter.py` (behaviours 1-6). Imports: `asyncio`,
  `from collections.abc import AsyncIterator, Callable, Mapping`, `from dataclasses import
  dataclass`, `from datetime import timedelta`, `from pathlib import Path`, `from uuid import
  UUID`, `structlog`, `from vibey.application.dto import EngineEvent, JobRecord, RunHandle,
  RunSpec`, `from vibey.application.interfaces import Clock, EngineAdapter, Logger`,
  `from vibey.application.interfaces.loop_routing import RoutedAdapterBinderInterface`,
  `from vibey.application.worker import EngineQueueSaturated`, `from vibey.domain.engine import
  ENGINE_ID_PARSER, EngineDescriptor, EngineId`, `from vibey.domain.interfaces.loop_services_config_interface
  import LoopConfigInterface`, `from vibey.domain.loop import LoopId`, `from vibey.domain.run_protocol
  import RunAccepted, RunPurpose, RunRequest, RunResult, RunRouted, RunSupersede`,
  `from vibey.infrastructure.engines.run_dir import RunDirTailer`,
  `from vibey.infrastructure.loop_service.interfaces.client_interface import LoopClientInterface`.
  Wherever `build_argv` actually lives (found in step 1's precondition), import it from there.
  `__all__ = ["RoutedAdapterBinder", "ServiceEngineAdapter"]`. Module docstring: ADR-0046 §3's
  service-mode adapter; the descriptor is known before `start` (step 4 of the flow); the tailer
  reads the same shared-volume evidence a subprocess adapter would.
- **`src/vibey/infrastructure/loop_service/client.py`** (`edit_file`, only if step 3's grep shows
  `submit_and_wait` has no way to observe acceptance separately from the terminal result): add the
  one additive keyword `on_accepted` and call it once, right where the method currently observes a
  `RunAccepted` message; every existing call site and test of `submit_and_wait` keeps working
  unedited, because the new keyword defaults to `None`.
- **New** `tests/infrastructure/loop_service/test_adapter.py`.

## Acceptance criteria
- [ ] `isinstance(ServiceEngineAdapter(...), EngineAdapter)` and `isinstance(RoutedAdapterBinder(...),
      RoutedAdapterBinderInterface)`.
- [ ] `start()` raises `EngineQueueSaturated` when no seat accepts the run within
      `run_queue_wait_seconds`, and returns a populated `RunHandle` when one does.
- [ ] `tail()` yields the same translated events a subprocess adapter would, read from the shared
      run directory, and stops once the remote run's terminal `RunResult` arrives.
- [ ] `RoutedAdapterBinder.bind` returns an adapter whose `descriptor` matches the routed engine,
      and raises for an engine with no configured descriptor.
- [ ] No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`; `tests/meta/patching_baseline.json`
      does not change; `tests/fakes/test_port_parity.py` passes.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_adapter.py`. Use `FakeLoopClient` (lane `loops-client`)
scripted with `results={run_id: RunResult(...)}`, `descriptor=BY_ENGINE_ID[EngineId.SOVEREIGNLOOP]`,
`config=LoopConfig()`, a `_Clock` fixed at `NOW`, `caller="w1"`. Write `events.jsonl` and
`meta.json` under `tmp_path / <descriptor.state_dir> / "runs" / <run_id>` before tailing, exactly
as `tests/infrastructure/engines/test_run_dir.py` already does for the subprocess tailer.
- `test_start_builds_the_run_request_from_the_spec_and_returns_a_handle`: a `RunSpec` with
  `worktree_path=tmp_path`, `effort=Effort.LOW`; after `start()`, the client's `submitted[0]`
  (or the equivalent recorded call) has `cwd == str(tmp_path)`, `run_dir ==
  f"{descriptor.state_dir}/runs/{run_id}"`, `args == build_argv(descriptor, spec)`,
  `route_id` matching what was bound; the returned handle's `run_id`/`pid`/`run_dir` match.
- `test_a_supersede_key_becomes_a_run_supersede`: `spec.supersede_key == "job-1"`,
  `spec.attempt == 2` → the published request's `supersedes == RunSupersede("job-1", 2)`.
- `test_start_raises_saturated_when_nothing_accepts_in_time`: a client scripted to never accept
  (or a `LoopConfig` with `run_queue_wait_seconds` set very small) → `pytest.raises(EngineQueueSaturated)`.
- `test_tail_translates_events_from_the_shared_run_directory`: write two lines of `events.jsonl`
  and a finished `meta.json` before calling `tail`; the yielded events match what
  `RunDirTailer` alone would give for the same files.
- `test_tail_stops_once_the_remote_result_arrives`: an empty `events.jsonl`, no `meta.json`, and a
  scripted terminal `RunResult` that resolves promptly → `tail` ends within the tailer's own grace
  window, yielding nothing.
- `test_release_diagnostics_forgets_the_run` (only if `EngineAdapter` declares it): after
  `release_diagnostics(handle)`, `_exit_code(handle.run_id) is None` even after the background
  task resolved.
- `test_the_binder_builds_the_routed_adapter`: `RoutedAdapterBinder(client=..., config=...,
  clock=..., descriptors=BY_ENGINE_ID, caller="w1").bind(routed, job=make_job(uuid4()))` returns a
  `ServiceEngineAdapter` whose `descriptor` matches `routed.engine_id`.
- `test_the_binder_refuses_an_unconfigured_engine`: a `routed.engine_id` outside `descriptors` →
  `pytest.raises(ValueError)`.
- `test_classes_satisfy_their_interfaces`: `isinstance` checks of behaviour 2's acceptance
  criteria list.

## Checks the lane must run (all must pass)
```bash
export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/infrastructure/engines/test_run_dir.py tests/application/test_conformance.py tests/fakes
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
git status --short
```

## Out of scope
- `send_prompt`, `stop`, `resume`, `preflight`, `help_text` and any other `EngineAdapter` method
  beyond `start`/`tail`/`release_diagnostics` (lane `loops-service-adapter-control`).
- `LoopClient` itself (lane `loops-client`) beyond the one additive keyword this lane may add.
- Wiring `RoutedAdapterBinder` and `ServiceEngineAdapter` into composition (lanes
  `loops-adapter-factory`, `loops-invocation-composition`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Protected tests
  are never edited.
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject. Follow
  `EDITING-RULES.md`.

**Depends on:** `loops-client`, `loops-queue-saturated`, `split-367-1-run-dir`, `fakes-ledger`.

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
