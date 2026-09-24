## Title
feat(cli): DESIGN, DECOMPOSE and every other pinned command run through the composed command executor

ADR-0046 lane L61 (slug `loops-invocation-cli`).

## Why
`loops-cli-provider-name`'s own out-of-scope note names this lane directly: "The four
`AsyncSubprocessExecutor()` sites (lane `loops-invocation-cli`)." Draft ADR-0046 §3, "Pinned runs
send one message" (`STORM/specs/ADR-two-loops.md:181`):
"These are DESIGN and DECOMPOSE through the command executor". `loops-invocation-composition`
built the two things this lane wires together: `AppResources.loop_client` (non-`None` only in
service mode) and the invocation mode itself. §2's closing paragraph keeps subprocess mode's
behaviour "unchanged" (12.c), so this lane's whole job is: at each of the four call sites, build
`LoopCommandExecutor` instead of `AsyncSubprocessExecutor` when (and only when) invocation mode is
`"service"`, and change nothing about what either executor is asked to run.

## Required behaviour
1. **`grep -rn "AsyncSubprocessExecutor(" src/vibey` first.** There must be exactly four call
   sites (the number this ADR's other lanes consistently cite); read each one's surrounding
   function to see how it is already composed (an argument, a module-level default, or built
   inline). **Stop and report** if the count is not four, or if a fifth, previously-unnoticed site
   exists: this lane changes exactly the sites the design sheet named, never a site it did not
   expect.
2. **One small composition helper**, `def build_command_executor(resources: AppResources, *,
   loop_id: LoopId = LoopId.SOVEREIGNLOOP) -> <the existing port>` in
   `src/vibey/infrastructure/loop_service/command_executor.py` (appended to the file
   `loops-command-executor` created):
   ```python
   def build_command_executor(
       resources: AppResources, *, loop_id: LoopId = LoopId.SOVEREIGNLOOP
   ) -> CommandExecutorPort:  # the exact name found in loops-command-executor's own grep
       if resources.loop_client is None:
           return AsyncSubprocessExecutor()
       engine_id = DEFAULT_ADAPTER[loop_id]
       return LoopCommandExecutor(
           loop_id=loop_id,
           engine_id=engine_id.value,
           client=resources.loop_client,
           config=resources.invocation.loop_services.for_loop(loop_id),
           clock=resources.clock,
           caller=resources.worker_owner,
       )
   ```
   (`resources.invocation` and `resources.worker_owner` are whatever `loops-invocation-composition`
   actually named its equivalent fields; read `bootstrap_interface.py` first and adjust the
   attribute names to match exactly.) This one function is the **only** place that decides between
   the two executors; every call site becomes `executor = build_command_executor(resources)`
   (or, for the one call site that is not itself holding an `AppResources`, whatever narrower
   arguments that site already has -- thread `loop_client`/`invocation`/`clock`/`worker_owner`
   through to it rather than reconstructing `AppResources` there).
3. **Each of the four call sites** (found in step 1) is edited to call
   `build_command_executor(...)` in place of `AsyncSubprocessExecutor()`, with every other
   argument to whatever consumes the executor left exactly as it is. No call site's *behaviour*
   changes when invocation mode is `"subprocess"` (the helper falls straight through to
   `AsyncSubprocessExecutor()`), so every existing test at every one of the four sites must pass
   unedited under the default mode.
4. **`vibey doctor`** (or wherever the CLI already reports the active invocation mode, if
   anywhere) gains one line, only if `installer-doctor` or an earlier lane already established a
   place for such a fact; if no such place exists yet, this lane adds none rather than inventing
   an output surface no other lane expects (`loops-doctor-legacy-spellings` owns the doctor
   output's structure, and it landed already; do not add unrelated new sections to `doctor` here).

## Where to change
- **Precondition.** Run the `grep` of behaviour 1 and follow its stop rule before editing
  anything.
- `src/vibey/infrastructure/loop_service/command_executor.py` (`edit_file`, over 100 lines after
  `loops-command-executor`): append `build_command_executor` (behaviour 2), plus its imports
  (`AsyncSubprocessExecutor` from wherever it lives today, `DEFAULT_ADAPTER` and `LoopId` from
  `vibey.domain.loop`, `AppResources` from `vibey.bootstrap_interface`).
- Each of the four files the grep of step 1 finds (`edit_file` only): replace
  `AsyncSubprocessExecutor()` with `build_command_executor(resources)` (or the narrower call the
  site's own available arguments allow), adding `from vibey.infrastructure.loop_service.command_executor
  import build_command_executor` to each file's imports.
- New test file `tests/infrastructure/loop_service/test_invocation_cli.py`.

## Acceptance criteria
- [ ] `grep -c "AsyncSubprocessExecutor(" src/vibey/**/*.py` (excluding
      `command_executor.py`'s own fallback call inside `build_command_executor`) shows the same
      four occurrences moved into that one helper, and zero remaining outside it.
- [ ] Every existing test at all four call sites passes unedited under the default
      (`"subprocess"`) invocation mode.
- [ ] With `AppResources.loop_client` set, `build_command_executor` returns a
      `LoopCommandExecutor`; with it `None`, an `AsyncSubprocessExecutor`.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*` and `src/vibey/cli/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_invocation_cli.py`:
- `test_subprocess_mode_builds_the_local_executor`: `AppResources` with `loop_client=None` →
  `isinstance(build_command_executor(resources), AsyncSubprocessExecutor)`.
- `test_service_mode_builds_the_loop_executor`: `AppResources` with a `FakeLoopClient` set as
  `loop_client` → `isinstance(build_command_executor(resources), LoopCommandExecutor)`.
- `test_the_loop_executor_is_bound_to_the_sovereign_default_adapter`: the built
  `LoopCommandExecutor`'s configured `engine_id == EngineId.SOVEREIGNLOOP.value` by default.
- `test_every_existing_call_site_still_passes_under_subprocess_mode`: run each of the four
  existing test modules the grep of step 1 pointed at (name them explicitly here once step 1's
  grep result is known) and confirm they pass with no edits.

## Checks the lane must run (all must pass)
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/cli tests/test_bootstrap.py tests/test_bootstrap_invocation.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    git diff --stat

## Out of scope
- `LoopCommandExecutor` itself (lane `loops-command-executor`); `AppResources.loop_client` and
  the invocation-mode composition (lane `loops-invocation-composition`).
- `--provider` (lane `loops-cli-provider-name`, already landed).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-invocation-composition`, `loops-cli-provider-name`.

## Hard repository rules (always)
- `domain/` stays pure: no I/O, no async, no clock, no network. Enforced by `tests/domain/test_domain_purity.py`, which walks the AST.
- Dependencies point inward only: `domain -> application -> infrastructure -> cli`, enforced by `import-linter` (`uv run lint-imports`).
- `CreditsExhausted` never has a `resets_at` field. A capacity rejection always outranks a completion claim.
- Code lives in classes, and every class gets an interface declared beside it (ADR-0016, sub-doctrine 9.b): `pkg/x.py` implies `pkg/interfaces/x_interface.py` (or an entry in an existing `interfaces/` module in the same package). A module-level function is the method of last resort, and needs a written reason at its definition. Interfaces declare; they never consume, and no Protocol is declared outside a package named `interfaces`. (`build_command_executor` is a module-level function by written exception: it is a pure composition helper called by name from four unrelated call sites, exactly like `selection_inputs_for_job` elsewhere in this codebase, and it consumes nothing -- it only builds and returns.)
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
