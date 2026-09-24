## Title
feat(cli): vibey loop-service runs one router/seat-host process until a signal drains it

ADR-0046 lane L64 (slug `loops-cli-loop-service`).

## Why
The storm's settled CLI shape (`STORM-CONTEXT.md`, confirmed against ADR-0046 §11's Deployment
model, `STORM/specs/ADR-two-loops.md:314-323`):
`vibey loop-service --loop L [--role all|router|seat] [--seat N]... [--capacity N]` exits 0 after
a clean drain, 2 on bad usage or no AMQP URL, and 78 when the broker refuses a second consumer for
the same seat, with the exit message naming sub-doctrine 8.c ("a single instance per model").
Exit 78 already means "misconfigured" elsewhere in this family (`EXIT_CODE_BACKEND_MISCONFIGURED`,
`domain/engine.py:23`), and 8.c's own refusal (`LoopInstanceRefused`, lane `loops-seat-host-core`
and its router twin) is exactly that kind of fact: the operator asked for a second instance of a
model the broker will not permit, which is a configuration error to fix, not a transient one to
retry. §11 fixes every Deployment's `replicas` at 1 with **no value to change it**, so this
command is the only thing that ever calls `build_loop_service`, and a `helm install --wait` waits
on this process reaching "ready" -- which ADR-0046 §3 makes true "once it holds its exclusive
consumer, even if the model runtime (e.g. Ollama) is down" (the storm's own settled decision,
matching D1 throughout the seat-host lanes: a missing Ollama is logged, never fatal).

## Required behaviour
1. **`vibey loop-service`** (new Typer command in `src/vibey/cli/main.py`):
   ```python
   @app.command()
   def loop_service(
       loop: Annotated[str, typer.Option("--loop", help="sovereignloop or paidloop.")],
       role: Annotated[str, typer.Option("--role", help="all, router, or seat. Default: all.")] = "all",
       seat: Annotated[list[str] | None, typer.Option("--seat", help="Required, exactly once, with --role seat.")] = None,
       capacity: Annotated[int | None, typer.Option("--capacity", help="Override this process's seat prefetch.")] = None,
   ) -> None:
       """Run one router, seat host or the full loop until SIGTERM drains it (sub-doctrine 8.c)."""
   ```
   - `loop` must parse as a `LoopId` (`LOOP_ID_PARSER.known(loop)`); an unrecognized value prints
     `f"loop must be 'sovereignloop' or 'paidloop', not {loop!r}"` and `raise typer.Exit(2)`.
   - `role` must parse as a `LoopServiceRole`; an unrecognized value prints
     `f"--role must be 'all', 'router', or 'seat', not {role!r}"` and exits 2.
   - `seat` becomes `tuple(seat or ())`; every usage rule beyond "is it present" is
     `build_loop_service`'s own job (lane `loops-bootstrap-loop-service`) -- this command never
     duplicates that validation, it only converts the `ValueError` that function raises for bad
     usage into `typer.echo(str(exc)); raise typer.Exit(2)`.
2. **The run loop**:
   ```python
   config = load_config_from_path(Path.cwd() / "vibey.toml")  # or however the worker loads it today
   try:
       process = asyncio.run(
           build_loop_service(
               loop_id=loop_id, role=role_value, seats=seat, capacity=capacity, config=config,
               environ=os.environ, clock=SystemClock(), instance=f"{socket.gethostname()}-{os.getpid()}",
           )
       )
   except LoopServiceNotConfigured as exc:
       typer.echo(str(exc), err=True)
       raise typer.Exit(2) from exc
   except ValueError as exc:
       typer.echo(str(exc))
       raise typer.Exit(2) from exc

   async def _run() -> int:
       stopping = asyncio.Event()
       loop_ref = asyncio.get_running_loop()
       loop_ref.add_signal_handler(signal.SIGTERM, stopping.set)
       loop_ref.add_signal_handler(signal.SIGINT, stopping.set)
       try:
           await process.start()
       except LoopInstanceRefused as exc:
           typer.echo(f"{exc} (sub-doctrine 8.c: a single instance per model)", err=True)
           return 78
       run_task = asyncio.create_task(process.run_forever())
       await stopping.wait()
       await process.stop(grace_seconds=<config.loop_config.supersede_grace_seconds, or a fixed
       generous default such as 30.0 if that value is not reachable here>)
       run_task.cancel()
       with contextlib.suppress(asyncio.CancelledError):
           await run_task
       return 0

   raise typer.Exit(asyncio.run(_run()))
   ```
   The `LoopInstanceRefused` catch is placed around `process.start()` specifically, because that
   is the one call that opens every consumer (`SeatHost.consume`, `LoopRouter.start`'s own
   `consume`), and the exit-78 message must name sub-doctrine 8.c exactly as the storm's own
   settled wording requires.
3. **Readiness.** `process.start()` returning without raising is the readiness signal a Kubernetes
   probe reads (§11: "A seat host is ready once it holds its exclusive consumer, even if the model
   runtime … is down — it logs the fault and never exits for it"). This command adds **no**
   separate health-check server: `--role all`/`--role seat`'s seat hosts already log
   `seat_consuming` on success and (per `loops-model-runtime`'s own D1) never fail `start()` for a
   missing Ollama; a liveness/readiness probe wired at the chart layer (out of scope here) simply
   checks the process is running, which is true from the moment `start()` returns.
4. **SIGTERM/SIGINT both drain**, matching the family's existing worker convention
   (`vibey worker`'s own SIGTERM handling, ADR-0025/ADR-0026): a second signal while already
   draining is not specially handled by this lane (the OS default resumes if the process does not
   exit; no code here changes that).

## Where to change
- `src/vibey/cli/main.py` (`edit_file` only; well over 100 lines): the new command, added after
  the existing `worker` command (`grep -n "^def worker" src/vibey/cli/main.py` to place it
  immediately after that function's closing line, matching the file's existing command ordering).
- Imports added to `main.py`: `signal`, `socket`, `contextlib` (if not already imported);
  `from vibey.domain.loop import LOOP_ID_PARSER`; `from vibey.infrastructure.loop_service.bootstrap
  import LoopServiceNotConfigured, build_loop_service`; `from vibey.infrastructure.loop_service.service_process
  import LoopServiceRole`; `from vibey.domain.errors import LoopInstanceRefused`.
- New test file `tests/cli/test_loop_service_command.py`.

## Acceptance criteria
- [ ] An unrecognized `--loop` or `--role` value exits 2 with the exact message given.
- [ ] No `VIBEY_BUS_AMQP_URL` exits 2 with `LoopServiceNotConfigured`'s own message.
- [ ] A `--role seat` invocation with zero or more than one `--seat` exits 2 (via
      `build_loop_service`'s `ValueError`, translated by this command).
- [ ] `LoopInstanceRefused` from `process.start()` exits 78, and the printed line contains
      "sub-doctrine 8.c" and "a single instance per model".
- [ ] `SIGTERM` and `SIGINT` each drain the process and exit 0.
- [ ] 100% branch coverage of `src/vibey/cli/*`.

## Tests to write first (TDD)
`tests/cli/test_loop_service_command.py` (`CliRunner`; a database-backed
`load_config_from_path`/equivalent may need `VIBEY_TEST_DATABASE_URL` if the worker's own config
loader does -- match whatever `tests/cli/test_operational_commands.py` already needs for
`worker`). Inject a fake `build_loop_service` at whatever seam the command actually calls through
(a keyword override on the Typer command function is not idiomatic for Typer; instead, this test
module composes `build_loop_service` itself against a `FakeLoopServiceProcess`
(`tests.fakes.loops`) by constructing the CLI's own async runner function directly, bypassing
Typer's own argument parsing for the process-lifecycle tests, and uses `CliRunner` only for the
argument-validation tests that never reach `build_loop_service` at all):
- `test_an_unknown_loop_exits_2`: `["loop-service", "--loop", "bogus"]` → exit 2, message contains
  `"bogus"`.
- `test_an_unknown_role_exits_2`: `["loop-service", "--loop", "sovereignloop", "--role", "bogus"]`
  → exit 2.
- `test_no_amqp_url_exits_2`: valid `--loop`/`--role`, no `VIBEY_BUS_AMQP_URL` in the runner's
  environment → exit 2, message contains `"VIBEY_BUS_AMQP_URL"`.
- `test_seat_role_without_a_seat_exits_2`: `--role seat` with no `--seat` → exit 2.
- `test_a_refused_instance_exits_78_naming_8c`: with the process-lifecycle runner built directly
  (not through `CliRunner`) and a process double whose `start()` raises `LoopInstanceRefused`
  → the coroutine's own return value is `78`, and the printed line contains "sub-doctrine 8.c" and
  "a single instance per model".
- `test_sigterm_drains_and_exits_0`: build the async runner with a `FakeLoopServiceProcess`; set
  its own stopping signal directly (rather than sending a real OS signal in the test) to prove the
  drain path; the coroutine returns `0`, and the fake's `calls` end with `"stop:<grace>"`.
- `test_readiness_is_simply_start_returning`: `FakeLoopServiceProcess().start()` completing without
  raising is asserted as the whole readiness contract (no separate health endpoint exists to test).

## Checks the lane must run (all must pass)
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli/test_loop_service_command.py tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- `build_loop_service` and `LoopServiceProcess` themselves (their own lanes).
- The chart's readiness/liveness probe configuration (a chart lane, not this one).
- `vibey loop submit` (lane `loops-cli-loop-submit`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-bootstrap-loop-service`.

## Hard repository rules (always)
- `domain/` stays pure: no I/O, no async, no clock, no network. Enforced by `tests/domain/test_domain_purity.py`, which walks the AST.
- Dependencies point inward only: `domain -> application -> infrastructure -> cli`, enforced by `import-linter` (`uv run lint-imports`).
- `CreditsExhausted` never has a `resets_at` field. A capacity rejection always outranks a completion claim.
- Code lives in classes, and every class gets an interface declared beside it (ADR-0016, sub-doctrine 9.b): `pkg/x.py` implies `pkg/interfaces/x_interface.py` (or an entry in an existing `interfaces/` module in the same package). A module-level function is the method of last resort, and needs a written reason at its definition. Interfaces declare; they never consume, and no Protocol is declared outside a package named `interfaces`. (A Typer command function is a module-level function by written exception: Typer commands are always declared this way throughout `cli/main.py`, and this lane follows the file's own established convention rather than introducing a class-based command the rest of the file does not use.)
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
