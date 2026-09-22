## Title
feat(bootstrap): build_loop_service composes one LoopServiceProcess from [loop_services] and CLI arguments

ADR-0046 lane L63 (slug `loops-bootstrap-loop-service`).

## Why
`bootstrap.py`'s `build_app`/`build_full_worker` are the sole composition root for the worker
(ADR-0002, CLAUDE.md's layer map: "the sole composition root"). `vibey loop-service` needs its own
composition root beside them, because it composes an entirely different runtime shape -- a
router, seat hosts and their consumers, never a `JobRepository` or a `PhaseLedger` -- from the
**same** `[loop_services]` configuration `loops-config-loop-services` declared, plus the CLI's own
`--loop`/`--role`/`--seat`/`--capacity` flags (ADR-0046's settled CLI shape, confirmed by the
storm's own settled-decisions record: `vibey loop-service --loop L [--role all|router|seat]
[--seat N]... [--capacity N]`). `loops-config-loop-services`'s own spec leaves `state_dir`'s empty
default unresolved on purpose: `"state_dir: '' (resolved at composition by lane
loops-bootstrap-loop-service)"` -- this lane is where that resolution happens, exactly as
`bootstrap.py` resolves `database_url()` and other environment-derived defaults for the worker.
Draft ADR-0046 §2 ("The loop's cursors persist, per project, in its own state directory (§10)")
and §10's `RunResultStore`/`RouteStore`/`LoopCursorStore` (which each take a `root: Path`) all
need that resolved directory, once, at composition time -- never re-derived per call.

## Required behaviour
1. **`def resolve_loop_state_dir(configured: str, *, loop_id: LoopId) -> Path`** in
   `src/vibey/infrastructure/loop_service/bootstrap.py` (new): `Path(configured)` when `configured`
   is non-empty (already validated absolute by `loops-config-loop-services`'s parser); otherwise
   `platformdirs.user_state_path("vibey") / "loop_services" / loop_id.value`. This function is
   pure given its `configured` argument, but the module it lives in is infrastructure (it touches
   `platformdirs`, which resolves a real OS-specific directory), so it stays out of `domain/`.
2. **`class LoopServiceNotConfigured(VibeyError)`**, mirroring `QueueBackendNotConfigured`'s and
   `EngineInvocationNotConfigured`'s own shape: raised with no AMQP URL, naming the remedy
   verbatim: `export VIBEY_BUS_AMQP_URL=amqp://USER:PASS@HOST:5672/`.
3. **`async def build_loop_service(*, loop_id: LoopId, role: LoopServiceRole, seats:
   Sequence[str], capacity: int | None, config: VibeyConfig, environ: Mapping[str, str], clock:
   Clock, instance: str, logger: Logger | None = None) -> LoopServiceProcess`** in the same
   module:
   1. `settings = EngineInvocationSettings.from_sources(config, environ)` (lane
      `loops-invocation-composition`); with `settings.amqp_url is None`, raise
      `LoopServiceNotConfigured`.
   2. `loop_config = settings.loop_services.for_loop(loop_id)`; `state_dir =
      resolve_loop_state_dir(settings.loop_services.state_dir, loop_id=loop_id)`.
   3. **Role validation, before anything is built** (bad usage is the CLI's own exit 2, but this
      function is where the shape is actually checked, so the CLI layer stays thin):
      - `role is LoopServiceRole.SEAT`: `len(seats) != 1` raises `ValueError("--role seat needs
        exactly one --seat")`; the named seat must be in `loop_config.effective_models(loop_id)`,
        else `ValueError(f"{seats[0]} is not a declared seat of {loop_id.value}")`.
      - `role is not LoopServiceRole.SEAT`: `seats` must be empty, else
        `ValueError(f"--seat is only valid with --role seat")`.
   4. `amqp = AmqpClient(AmqpSettings(settings.amqp_url, vhost=settings.vhost))` (connects
      lazily); `names = RunQueueNames(prefix=settings.prefix)`; `codec = RunProtocolCodec()`.
   5. **Build the seats this process hosts.** For `ALL`, every seat in
      `loop_config.effective_models(loop_id)`; for `SEAT`, the one named seat; for `ROUTER`, none.
      For each seat, build one `SeatHost(loop_id=loop_id, seat=seat, model=<seat if
      loop_id is SOVEREIGNLOOP else None>, amqp=amqp, names=names, codec=codec,
      executor=LocalRunExecutor(...), results=RunResultStore(codec=codec), config=loop_config,
      environ=environ, clock=clock, instance=instance, measurements=LoopMeasurementLog(state_dir /
      "measurements.jsonl"), prefetch=<capacity if given, else loop_config.prefetch_for(seat)>)`
      (lane `loops-seat-host-core`; `LocalRunExecutor` is lane `loops-local-run-executor`'s own
      class, built with `root=loop_config` -- wire whatever arguments that executor's own spec
      names, read it first if it has landed by this point).
   6. **Router-hosted components**, only for `ALL`/`ROUTER`: `route_store =
      RouteStore(state_dir)`; `cursor_store = LoopCursorStore(state_dir)`; `backlog =
      SeatBacklog()`; `router = LoopRouter(loop_id=loop_id, amqp=amqp, names=names, codec=codec,
      config=loop_config, seats=<{seat: (model if sovereign else seat) for seat in ...}>,
      adapters=<the adapters this loop may run -- for sovereignloop, {"sovereignloop", "vscode",
      "opencode"} intersected with what is actually declared; for paidloop,
      frozenset(loop_config.effective_models(loop_id))>, default_adapter=DEFAULT_ADAPTER[loop_id].value,
      routes=route_store, cursors=cursor_store, chooser=SeatChooser(), residency=ResidencyPolicy(),
      declarations=loop_config.declarations(), default_model=loop_config.default_model,
      resident_model=<a callable the scheduler overwrites once built, or `lambda: None` for
      `ROUTER`, which never resolves a model itself>, backlog=backlog,
      measurements=LoopMeasurementLog(state_dir / "measurements.jsonl"), clock=clock)`;
      `dead_letters = DeadLetterReplier(loop_id=loop_id, amqp=amqp, names=names, codec=codec,
      seats=list(seat_hosts), clock=clock, measurements=<the same log>)`;
      `control = ControlConsumer(loop_id=loop_id, amqp=amqp, names=names, codec=codec,
      hosts=seat_hosts)`; `probes = ProbeConsumer(loop_id=loop_id, amqp=amqp, names=names,
      codec=codec, resident_model=<the same callable>, cache=ProbeCache(), clock=clock,
      measurements=<the same log>, submit=<a `LoopClient`-shaped submitter bound to this same
      `amqp`, built once here and reused, per 10.e: a probe consumer and the router both need to
      submit runs to seats, so one `LoopClient` instance is shared between them the same way
      `loops-invocation-composition` shares one across every service adapter>)`.
   7. **The resident schedule, only for `ALL`**: `scheduler = ResidentSeatScheduler(loop_id=loop_id,
      hosts=seat_hosts, models={seat: (seat if loop_id is not LoopId.SOVEREIGNLOOP else <the
      model that seat's slug names -- the inverse of SeatSlug, so track {seat_slug: model_name}
      explicitly when building seat_hosts in step 5, rather than re-deriving it>) for seat in
      seat_hosts}, default_seat=<the default model's own slug for sovereignloop; the default
      adapter's own name for paidloop -- `ALL` is only ever built for sovereignloop in practice,
      since paidloop's seats are engine ids with no residency concept, but the class itself does
      not forbid it>, amqp=amqp, names=names, runtime=OllamaModelRuntime(base_url=<from
      `VIBEY_OLLAMA_URL`, environ>), schedule=ResidencySchedule(), backlog=backlog, config=
      loop_config, clock=clock, measurements=<the same log>)`; then `resident_model = lambda:
      scheduler.resident_seat` is wired back into `router`'s and `probes`' constructors (built
      after `scheduler`, in place of the placeholder of steps 6); and `host.set_on_run_finished(
      scheduler.on_run_finished)` for every seat host in `seat_hosts`.
   8. Return `LoopServiceProcess(role=role, router=<router or None>, dead_letters=<... or None>,
      control=<... or None>, probes=<... or None>, scheduler=<scheduler or None>,
      seats=seat_hosts)` (lane `loops-service-process`).
4. Every object this function builds that owns a background resource (`amqp`) is not itself
   closed by `build_loop_service`: the caller (`loops-cli-loop-service`) owns `amqp.close()` in
   its own `finally`, exactly as `build_app` owns its own AMQP client's lifecycle.

## Where to change
Line 1 of the new file is the provenance comment, copied byte for byte from line 1 of
`src/vibey/bootstrap.py`.
- **Preconditions.** `grep -n "class LocalRunExecutor" -r src/vibey/infrastructure/loop_service`
  and read its constructor before wiring step 5; adjust the argument names to match exactly.
- **New** `src/vibey/infrastructure/loop_service/bootstrap.py` (behaviours 1-4). This module
  imports from nearly every other `loop_service` module; keep the import list sorted and let
  `ruff check --fix --select I` order it. `__all__ = ["LoopServiceNotConfigured",
  "build_loop_service", "resolve_loop_state_dir"]`.
- New test file `tests/infrastructure/loop_service/test_bootstrap.py`.

## Acceptance criteria
- [ ] `resolve_loop_state_dir("", loop_id=LoopId.SOVEREIGNLOOP)` returns a path ending
      `loop_services/sovereignloop` under the platform's own state directory; a non-empty
      `configured` is returned unchanged as a `Path`.
- [ ] `build_loop_service` with no AMQP URL raises `LoopServiceNotConfigured` naming the remedy.
- [ ] `--role seat` with zero or more than one seat, or a seat not declared by the loop, raises
      `ValueError` before any AMQP connection is opened.
- [ ] `--role all` builds one seat host per declared seat, a router, all three router-hosted
      consumers, and a resident schedule wired to every host's `on_run_finished`.
- [ ] `--role router` builds a router and its three consumers, and no seat host or scheduler.
- [ ] `--role seat` builds exactly one seat host, and nothing else.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_bootstrap.py`. Use a minimal `VibeyConfig()` (defaults),
`environ={"VIBEY_BUS_AMQP_URL": "amqp://u:p@h:5672/"}`, a `_Clock`.
- `test_resolve_loop_state_dir_uses_the_platform_default_when_unset`: the returned path's last two
  parts are `("loop_services", "sovereignloop")`.
- `test_resolve_loop_state_dir_keeps_a_configured_absolute_path`: `resolve_loop_state_dir("/work/state",
  loop_id=LoopId.PAIDLOOP) == Path("/work/state")`.
- `test_no_amqp_url_raises_loop_service_not_configured`: `environ={}` →
  `pytest.raises(LoopServiceNotConfigured)` whose message names
  `export VIBEY_BUS_AMQP_URL=amqp://USER:PASS@HOST:5672/`.
- `test_role_seat_needs_exactly_one_seat`: `seats=()` and `seats=("a", "b")` both raise
  `ValueError` before `amqp.connect()` is ever called (no test double is even wired for the broker
  in this case, so a real `AmqpClient` object existing but never connected is proof enough).
- `test_role_seat_needs_a_declared_seat`: `seats=("bogus-model",)` raises `ValueError` naming it.
- `test_role_router_and_all_forbid_seat`: `role=ROUTER, seats=("gpt-oss-20b",)` raises
  `ValueError`.
- `test_role_all_builds_every_declared_seat_and_the_scheduler`: default sovereignloop config
  (one declared model, the 8.d default) → the returned `LoopServiceProcess` was built with a
  non-`None` `scheduler` and one seat (assert through the process's own observable behaviour,
  e.g. `isinstance(process, LoopServiceProcessInterface)` and a follow-up `await process.start()`
  against an `InMemoryAmqpClient`-backed `AmqpClient` substitute if the constructor accepts an
  injected connector the same way `AmqpClient` itself does -- inject via
  `AmqpClient(AmqpSettings(...), connector=<a fake connector>)` if `build_loop_service` exposes
  that seam, or otherwise assert on the pre-`start()` shape this function returns).
- `test_role_router_builds_no_seat_or_scheduler`.
- `test_role_seat_builds_only_its_one_host`.

## Checks the lane must run (all must pass)
```bash
export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/fakes
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
git status --short
```

## Out of scope
- The `vibey loop-service` CLI command, its exit codes and SIGTERM handling (lane
  `loops-cli-loop-service`).
- `LocalRunExecutor`, `OllamaModelRuntime`, `SeatChooser`, `ResidencyPolicy`, `ResidencySchedule`
  themselves (already-landed lanes; this lane only wires them).
- `EngineInvocationSettings` itself (lane `loops-invocation-composition`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Protected tests
  are never edited.
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject. Follow
  `EDITING-RULES.md`.

**Depends on:** `loops-service-process`, `loops-invocation-composition`.

## Hard repository rules (always)
- `domain/` stays pure: no I/O, no async, no clock, no network. Enforced by `tests/domain/test_domain_purity.py`, which walks the AST.
- Dependencies point inward only: `domain -> application -> infrastructure -> cli`, enforced by `import-linter` (`uv run lint-imports`).
- `CreditsExhausted` never has a `resets_at` field. A capacity rejection always outranks a completion claim.
- Code lives in classes, and every class gets an interface declared beside it (ADR-0016, sub-doctrine 9.b): `pkg/x.py` implies `pkg/interfaces/x_interface.py` (or an entry in an existing `interfaces/` module in the same package). A module-level function is the method of last resort, and needs a written reason at its definition. Interfaces declare; they never consume, and no Protocol is declared outside a package named `interfaces`. (`build_loop_service` and `resolve_loop_state_dir` are module-level functions by written exception: they are the composition root's own entry points, exactly like `build_app` and `database_url` elsewhere in `bootstrap.py`, called by name and never substituted at a seam.)
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
