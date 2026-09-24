## Title
feat(loop-service): LoopCommandExecutor runs a one-shot pinned command through a loop instead of a local subprocess

ADR-0046 lane L58 (slug `loops-command-executor`).

## Why
Draft ADR-0046 §10 (`STORM/specs/ADR-two-loops.md:304`)
names `infrastructure/loop_service/command_executor.py` directly, beside `client.py` and
`adapter.py`. §3, "Pinned runs send one message" (`:181`): "These are DESIGN and DECOMPOSE through
the command executor, and `vibey loop submit --engine`. The router routes the run request itself,
with the pin, and forwards it." At integration `d3b4a388`, DESIGN and DECOMPOSE's one-shot,
non-`EngineAdapter` command invocations (a `qwenloop design ...` call, and every other pinned
binary invocation that is not a BUILD job) go through an existing seam this design sheet calls the
**command executor** -- `AsyncSubprocessExecutor`, whose four call sites `loops-cli-provider-name`
names as out of scope for itself and defers to this lane's sibling, `loops-invocation-cli`: "The
four `AsyncSubprocessExecutor()` sites (lane `loops-invocation-cli`)." This lane builds the
service-mode twin of that executor -- `LoopCommandExecutor`, implementing the **same** existing
port `AsyncSubprocessExecutor` implements -- so `loops-invocation-cli` can swap one for the other
at each of those four call sites purely by construction, with no call site itself knowing which
mode it is in. Sub-doctrine 10.e (`doctrines.md:417`): the same port, never a second one.

## Required behaviour
1. **First, read the exact seam.** `grep -n "class AsyncSubprocessExecutor" -A 5 -r src/vibey`
   and read the interface it implements (its own `interfaces/*_interface.py` file, found the same
   way `fakes-process-executor`'s own fake targets it). This lane's class implements **that same**
   Protocol, with identical method names and signatures. Wherever this spec's assumed shape
   differs from what is actually declared, follow the declaration and say so in the commit body.
   The shape assumed below (`run(self, argv, *, cwd, timeout_seconds, env=None) ->
   CommandResult`-like) is this lane's best reconstruction from every sibling reference; adjust it
   to match reality before writing a line of implementation.
2. **`class LoopCommandExecutor`** in `src/vibey/infrastructure/loop_service/command_executor.py`,
   built as `LoopCommandExecutor(*, loop_id: LoopId, engine_id: str, client: LoopClientInterface,
   config: LoopConfigInterface, clock: Clock, caller: str, logger: Logger | None = None)`.
   - Its one execution method (name and signature from step 1's grep) builds a `RunRequest` the
     same way `loops-service-adapter-run`'s `ServiceEngineAdapter.start` does, with these
     differences suited to a one-shot pinned command rather than a BUILD run:
     - `purpose=RunPurpose.RUN` (a command executor invocation is a real unit of work whose output
       matters, not a preflight probe);
     - `capture_output=True` (the executor's whole contract is returning captured stdout/stderr,
       unlike a BUILD adapter, which tails `events.jsonl` instead);
     - `run_dir=None` (a one-shot command writes no `events.jsonl` a tailer would follow; its
       entire result is the captured output in the terminal `RunResult`);
     - `route_id=None`, `model_pin=None` (a command executor call is always a fresh pin on
       `self._engine_id`, never a job already routed by the outer layer -- it reaches its seat
       through `loops-router-forwarding`'s pinned-request path, addressed by `engine_id` alone);
     - `supersedes=None` (a one-shot command is not a job attempt with a supersede key);
     - `deadline_seconds` and `start_by` come from the caller's own `timeout_seconds` argument
       (whatever the grep of step 1 names it), not from `LoopConfig.run_deadline_seconds`: a
       command executor caller already states how long it will wait, and that must be honoured
       exactly, both as the `RunRequest.deadline_seconds` the seat host enforces and as the
       `accept_wait`/`run_wait` this class passes to `submit_and_wait`.
   - `await self._client.submit_and_wait(request, accept_wait=<a fraction of the timeout, for
     example min(30, timeout_seconds)>, run_wait=timedelta(seconds=timeout_seconds))` -- a
     saturation (`EngineQueueSaturated`) here propagates to the caller exactly as it does for a
     BUILD adapter's `start`: **this lane never catches it**, so the surrounding invocation-mode
     composition (lane `loops-invocation-composition`) decides how DESIGN/DECOMPOSE handle it,
     exactly the way they already handle a local subprocess that could not even be spawned.
   - The `RunResult` is translated into whatever return shape the port declares (a result object
     carrying `exit_code`, `stdout`, `stderr` at minimum, from `RunResult.exit_code`,
     `RunResult.stdout`, `RunResult.stderr`); a `DEADLINE_EXCEEDED` or `REJECTED`/`SUPERSEDED`/
     `ABANDONED`/`DEAD_LETTERED` status is translated the same way a local subprocess's own
     timeout or spawn failure is translated today (copy that translation from
     `AsyncSubprocessExecutor` verbatim, found in step 1's grep, rather than inventing a second
     mapping from status to the port's own error shape).
3. **`src/vibey/infrastructure/loop_service/interfaces/command_executor_interface.py`**: this lane
   declares **no new Protocol** -- it satisfies the existing one found in step 1. If that existing
   interface module already lives outside `infrastructure/loop_service/`, this lane's class simply
   imports and implements it from there; it does not duplicate the declaration.
4. **Fake.** `fakes-process-executor` already registers the existing port's fake for
   `AsyncSubprocessExecutor`; because `LoopCommandExecutor` satisfies the **same** port, that one
   fake already covers both production implementations, and no new fake or registry entry is
   needed by this lane. If `fakes-process-executor`'s fake is keyed to `AsyncSubprocessExecutor`'s
   concrete type rather than to the shared interface, **stop and report**: the family fake must be
   registered against the interface (`tests/fakes/registry.py`'s convention throughout this ADR),
   and this lane cannot silently work around a registration keyed the wrong way.

## Where to change
Line 1 of every new file is the provenance comment, copied byte for byte from line 1 of
`src/vibey/infrastructure/loop_service/client.py`.
- **Preconditions.** Run the `grep` of behaviour 1 and behaviour 4's check before writing anything.
- **New** `src/vibey/infrastructure/loop_service/command_executor.py` (behaviour 2). Imports:
  `from datetime import timedelta`, `structlog`, `from vibey.application.interfaces import Clock,
  Logger`, `from vibey.domain.interfaces.loop_services_config_interface import
  LoopConfigInterface`, `from vibey.domain.loop import LoopId`, `from vibey.domain.run_protocol
  import RunPurpose, RunRequest, RunStatus`,
  `from vibey.infrastructure.loop_service.interfaces.client_interface import LoopClientInterface`,
  plus the executor port's own module (found in step 1). `__all__ = ["LoopCommandExecutor"]`.
  Module docstring: ADR-0046 §3's pinned-command path; the same port `AsyncSubprocessExecutor`
  implements, so DESIGN/DECOMPOSE and `vibey loop submit` cannot tell which mode they run in.
- No new interface module (behaviour 3); no fake or registry edit unless behaviour 4's stop rule
  fires.
- **New** `tests/infrastructure/loop_service/test_command_executor.py`.

## Acceptance criteria
- [ ] `isinstance(LoopCommandExecutor(...), <the existing port>)` holds.
- [ ] A successful run's `exit_code`/`stdout`/`stderr` are translated identically to how
      `AsyncSubprocessExecutor` translates a local process's own output.
- [ ] The caller's own `timeout_seconds` becomes both the `RunRequest.deadline_seconds` the seat
      host enforces and the bound this class itself waits, never `LoopConfig`'s own defaults.
- [ ] A saturated submission propagates `EngineQueueSaturated` unchanged; a non-`EXITED` terminal
      status is translated exactly as the existing local-subprocess failure path already is.
- [ ] No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`;
      `tests/meta/patching_baseline.json` does not change.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_command_executor.py`. Use `FakeLoopClient` (lane
`loops-client`), `LoopConfig()`, a `_Clock` fixed at `NOW`.
- `test_a_pinned_run_carries_no_route_dir_or_supersede`: after one execution, the published
  request has `route_id is None`, `run_dir is None`, `supersedes is None`, `capture_output is True`,
  `purpose is RunPurpose.RUN`.
- `test_the_callers_timeout_becomes_the_deadline`: `timeout_seconds=45` → the published request's
  `deadline_seconds == 45`, and `submit_and_wait` was awaited with `run_wait ==
  timedelta(seconds=45)`.
- `test_a_successful_run_translates_stdout_and_exit_code`: a scripted `RunResult(status=EXITED,
  exit_code=0, stdout="ok", stderr="")` → the returned result's fields match, in whatever shape
  the existing port declares.
- `test_a_saturated_submission_propagates_unchanged`: a client that raises `EngineQueueSaturated`
  → the same exception propagates from this class's own call, unchanged.
- `test_a_non_exited_terminal_status_is_translated_like_a_local_failure`: a scripted
  `DEADLINE_EXCEEDED` result → the same translation `AsyncSubprocessExecutor` gives a local
  timeout (copy that assertion from the existing port's own test file, adapted to this class).
- `test_classes_satisfy_the_existing_port`: `isinstance(LoopCommandExecutor(...), <port>)`.

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
- `AsyncSubprocessExecutor` itself and its four call sites (lane `loops-invocation-cli`).
- Wiring `LoopCommandExecutor` into composition (lane `loops-invocation-composition`).
- `LoopClient` (lane `loops-client`) beyond calling its existing `submit_and_wait`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Protected tests
  are never edited.
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject. Follow
  `EDITING-RULES.md`.

**Depends on:** `loops-client`, `loops-queue-saturated`, `fakes-process-executor`.

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
