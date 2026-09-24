## Title
feat(cli): vibey loop submit sends one pinned run and reports exactly how it ended

ADR-0046 lane L65 (slug `loops-cli-loop-submit`).

## Why
The storm's settled CLI shape (`STORM-CONTEXT.md`, confirmed against ADR-0046 §3's "Pinned runs
send one message" and §5's capacity table,
`STORM/specs/ADR-two-loops.md:181`, `:226-236`):
`vibey loop submit` sends one pinned run: exits 75 on saturation, 69 when the run is unroutable.
Exit 75 (`EX_TEMPFAIL`, the family's existing convention for "try again, this is not your fault")
matches §5's own classification of queue saturation: "busy is not 'cannot carry' (8.a)" -- a
retryable condition, never a permanent refusal. Exit 69 (`EX_UNAVAILABLE`) matches `UNROUTABLE`,
which §5 also calls "a routing fact, not a capacity state": the pin named an engine or model this
loop provably cannot run right now, which is a different kind of failure than "everyone is busy"
and deserves its own exit code so a caller (a script, a CI step) can tell the two apart without
parsing text. This command is the third and last consumer of the pinned-run machinery
`loops-router-forwarding` built: DESIGN and DECOMPOSE go through `loops-command-executor` instead
(a one-shot invocation with captured output, no operator watching); `vibey loop submit` is the
**human-facing** entry point to the same mechanism, for an operator who wants to push one
specific run at a specific engine and see how it went.

## Required behaviour
1. **`vibey loop submit`** (a new Typer sub-command; group it under whatever sub-app already
   holds related `loop` commands, or create `loop_app = typer.Typer()` mounted as
   `app.add_typer(loop_app, name="loop")` if none exists yet -- `grep -n "add_typer" src/vibey/cli/main.py`
   first to see the file's existing convention and follow it exactly):
   ```python
   @loop_app.command("submit")
   def loop_submit(
       engine: Annotated[str, typer.Option("--engine", help="The adapter to pin this run to, e.g. claudeloop or sovereignloop.")],
       prompt_file: Annotated[Path, typer.Argument(help="A plan or prompt file to run.")],
       cwd: Annotated[Path, typer.Option("--cwd", help="The worktree to run in. Default: the current directory.")] = Path.cwd(),
       model: Annotated[str | None, typer.Option("--model", help="A model to pin (sovereignloop only).")] = None,
       timeout_seconds: Annotated[int, typer.Option("--timeout-seconds")] = 3600,
   ) -> None:
       """Send one pinned run through its loop and report how it ended."""
   ```
2. **Resolution.** `engine_id = ENGINE_ID_PARSER.known(engine)`; unrecognized → print
   `f"unknown engine {engine!r}"` and `raise typer.Exit(2)`. `loop_id =
   LOOP_MEMBERSHIP.loop_of(BY_ENGINE_ID[engine_id])` (an engine with no descriptor at all is the
   same exit-2 path, since `BY_ENGINE_ID[engine_id]` would raise `KeyError` -- catch it and print
   the same unknown-engine message).
3. **Composition.** Build `settings = EngineInvocationSettings.from_sources(<load the working
   directory's own vibey.toml if present, else defaults>, os.environ)` (lane
   `loops-invocation-composition`'s value type, reused here rather than duplicated); no AMQP URL →
   print the same two-remedy message `LoopServiceNotConfigured`/`EngineInvocationNotConfigured`
   already use and `raise typer.Exit(2)`. Build one `AmqpClient`, one `LoopClient` (lane
   `loops-client`), `await client.start()`.
4. **The run.** Build
   ```python
   request = RunRequest(
       run_id=uuid4(), loop_id=loop_id, engine_id=engine_id.value, route_id=None,
       model_pin=model, purpose=RunPurpose.RUN, args=("run", str(prompt_file)),
       cwd=str(cwd.resolve()), run_dir=f"{BY_ENGINE_ID[engine_id].state_dir}/runs/{run_id}",
       supersedes=None, deadline_seconds=timeout_seconds,
       start_by=SystemClock().now() + timedelta(seconds=settings.loop_services.for_loop(loop_id).run_queue_wait_seconds),
       capture_output=False, requested_at=SystemClock().now(), caller="vibey loop submit",
   )
   ```
   then
   ```python
   try:
       result = await client.submit_and_wait(
           request, accept_wait=timedelta(seconds=settings.loop_services.for_loop(loop_id).route_wait_seconds),
           run_wait=timedelta(seconds=timeout_seconds),
           on_progress=lambda p: typer.echo(p.line),
       )
   except EngineQueueSaturated as exc:
       typer.echo(str(exc), err=True)
       raise typer.Exit(75) from exc
   ```
5. **Reporting the result.** `RunStatus` (lane `loops-run-protocol-messages`) already has an
   `UNROUTABLE` member, and `loops-router-forwarding`'s pinned-forward path answers exactly that
   status directly (never a dead letter) when a pin cannot be placed on any seat -- so this
   command's whole reporting step is a plain match on `result.status`, with no ambiguity to
   resolve at implementation time:
   - `RunStatus.UNROUTABLE`: print `result.detail` to stderr, `raise typer.Exit(69)`.
   - `RunStatus.EXITED`: print nothing extra (progress lines were already echoed live);
     `raise typer.Exit(result.exit_code or 0)`.
   - Any other terminal status (`SUPERSEDED`, `ABANDONED`, `REJECTED`, `DEADLINE_EXCEEDED`,
     `DEAD_LETTERED`): print `result.detail` and `raise typer.Exit(1)`.
6. **Cleanup.** `await client.stop()` and close the AMQP client in a `finally`, whatever exit path
   was taken.

## Where to change
- `src/vibey/cli/main.py` (`edit_file` only): the new command (behaviours 1-6), added beside
  `loop-service` (lane `loops-cli-loop-service`, landed immediately before this one in the queue).
- Imports added: `from uuid import uuid4`; `from vibey.application.worker import
  EngineQueueSaturated`; `from vibey.domain.engine import BY_ENGINE_ID, ENGINE_ID_PARSER`;
  `from vibey.domain.loop import LOOP_MEMBERSHIP`; `from vibey.domain.run_protocol import
  RunPurpose, RunRequest, RunStatus`; `from vibey.infrastructure.loop_service.client import
  LoopClient`; `from vibey.infrastructure.loop_service.bootstrap import
  LoopServiceNotConfigured` (or wherever the shared two-remedy message actually lives by this
  point -- reuse it, never restate the string a third time).
- New test file `tests/cli/test_loop_submit_command.py`.

## Acceptance criteria
- [ ] An unknown `--engine` exits 2 before any AMQP connection.
- [ ] No AMQP URL exits 2 with the shared two-remedy message.
- [ ] A saturated submission exits 75, with the exception's own message on stderr.
- [ ] An unroutable pin exits 69, with a reason on stderr.
- [ ] A successful run exits with the run's own exit code (0 on a normal success); progress lines
      are echoed live as they arrive.
- [ ] Every other terminal status exits 1 with its detail printed.
- [ ] 100% branch coverage of `src/vibey/cli/*`.

## Tests to write first (TDD)
`tests/cli/test_loop_submit_command.py`. Inject a `FakeLoopClient` (lane `loops-client`) at
whatever composition seam the command actually offers (if `main.py`'s existing commands take no
injected client and instead always build a real one, follow that file's own established pattern
for testing such commands -- likely a monkeypatched **environment variable** pointing
`AsyncioProcessSpawner`-style tests at a fake, or a small factory function this command calls that
a test overrides via dependency injection at the composition-root level, matching whatever
`tests/cli/test_operational_commands.py` already does for `worker`'s own AMQP-backed paths once
`rmq-r17` lands -- copy that pattern exactly rather than inventing a new one for this command).
- `test_an_unknown_engine_exits_2`: `["loop", "submit", "--engine", "bogus", "plan.md"]` → exit 2.
- `test_no_amqp_url_exits_2`: valid engine, no `VIBEY_BUS_AMQP_URL` → exit 2, message names both
  remedies.
- `test_a_saturated_submission_exits_75`: a client scripted to raise `EngineQueueSaturated` →
  exit 75, message on stderr.
- `test_an_unroutable_pin_exits_69`: a client scripted with `RunResult(status=RunStatus.UNROUTABLE,
  detail="no route or pinned seat for run <id> on sovereignloop", ...)` → exit 69, that detail on
  stderr.
- `test_a_successful_run_exits_with_its_own_code`: a scripted `RunResult(status=EXITED,
  exit_code=0, ...)` → exit 0; `exit_code=3` → exit 3.
- `test_progress_lines_are_echoed_live`: a scripted sequence of `RunProgress` messages → each
  line appears in the command's stdout, in order, before the final exit.
- `test_other_terminal_statuses_exit_1`: `ABANDONED`, `REJECTED`, `SUPERSEDED`,
  `DEADLINE_EXCEEDED` and `DEAD_LETTERED` each exit 1 with `result.detail` printed.

## Checks the lane must run (all must pass)
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli/test_loop_submit_command.py tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- `LoopClient`, `RunRequest` construction rules beyond what a pinned submit needs, and the
  unroutable/dead-letter answer shape itself (their own already-landed lanes; this lane only
  reads and reports them).
- `vibey loop-service` (lane `loops-cli-loop-service`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-cli-loop-service`.

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
