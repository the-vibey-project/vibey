## Title
feat(cli): vibey test status, dead-letters and requeue — see the harness and grant a parked run

## Why
Sub-doctrine 8.e (ratified, `src/vibey_tools/gh/docs/doctrines.md:283-286`): a dead-lettered run is
kept "with its evidence, where a human or a repair lane can see it". Draft ADR-0045 §9 makes
`vibey test requeue` the grant that answers a park — ADR-0024's "every bounded ladder parks with a
grant" — and never the automatic retry 8.e forbids. `vibey test status` says who holds the
machine's lock and how to stop an unwanted run (§11: send the holder SIGTERM; the instance records
it `abandoned`), and it shows what is running and what was answered recently, so status stays
evidence-bounded (10.f) rather than guessed.

## Required behaviour
In `src/vibey/cli/test_harness.py` (add; harness-T15b and T15 wrote it). Each command class takes
`composition_factory: Callable[..., TestHarnessCompositionInterface] = build_test_harness` and
`config_loader` like `TestRunCommand`, echoes with `typer.echo`, and is found by its typer function
with `ctx.find_object(<Class>) or <DEFAULT>` (module-level default bindings, each with the reason
comment). The composition exposes everything used here (harness-T15a): `settings`, `clock`,
`requester`, `store()`, `lock()`, `builder()` and `client()`.
1. **`TestStatusCommand.run(self, *, as_json: bool, config: Path | None, environ) -> int`**
   (`vibey test status [--json] [--config FILE]`):
   - `holder: pid <pid> (<alive|dead|unknown>) request <request_id or -> since <since or -> — stop it with: kill <pid>`
     from `composition.lock().holder()` (read keys with `.get`: `alive` missing prints `unknown`),
     or `holder: none`;
   - one line per `store.running()` attempt: `running: run <run_id> key <first 12> cwd <cwd> argv <argv joined by spaces>`;
   - one line per `store.recent_answers(10)`: `recent: <status> <outcome or -> run <run_id or -> key <first 12 or -> <backend>`.

   `--json` prints one object `{"holder": <mapping or null>, "running": [<encoded records>], "recent": [<encoded answers>]}`
   using `TestRunRecordCodec` / `TestHarnessCodec` `encode`. Exit 0.
2. **`TestDeadLettersCommand.run(self, *, as_json: bool, include_answered: bool, config, environ) -> int`**
   (`vibey test dead-letters [--json] [--all] [--config FILE]`): one line per
   `store.dead_letters(include_answered=...)`:
   `<run_id> <outcome> <dead_lettered_at isoformat> <cwd> <argv joined> — <reason>`, with
   ` (answered)` appended when `store.is_answered(run_id)`. When `store.malformed()` is non-empty,
   a final line `malformed messages: <n> in <settings.state_dir>/malformed`. `--json` prints a JSON
   list of encoded dead letters. Always exit 0.
3. **`TestRequeueCommand.run(self, *, run_id: str, wait_seconds: int | None, full_output: bool, config, environ) -> int`**
   (`vibey test requeue RUN_ID [--wait-seconds N] [--full-output] [--config FILE]`):
   - an unknown `RUN_ID` (not a UUID, or no `store.dead_letter_by_run`) exits 2 with
     `no dead letter <run_id>`; an answered one exits 2 with `dead letter <run_id> is already answered`;
   - `env = dict(environ)` (`--wait-seconds` sets `VIBEY_HARNESS_WAIT_SECONDS`); for each name in
     `letter.env_names` missing from `env`, echo `warning: <name> is not set in this environment` to stderr;
   - `request = await composition.builder().build(cwd=Path(letter.cwd), argv=letter.selection.argv, gates=letter.selection.gates, fresh=False, grant=True, environ=env)`;
   - when `letter.record` is set and `request.environment != letter.record.environment`, echo
     `warning: the environment differs from the dead-lettered run's; this is a new key` to stderr;
   - `store.answer_dead_letter(DeadLetterAnswer(run_id=letter.run_id, answered_by=composition.requester, answered_at=composition.clock.now(), requeued_request_id=request.request_id))`;
   - `result = await (await composition.client()).submit(request)`; echo it through
     `TestRunReport` (harness-T15b) and exit with its `exit_code`.
4. **Interfaces** in `src/vibey/cli/interfaces/test_harness_interface.py`:
   `TestStatusCommandInterface`, `TestDeadLettersCommandInterface`, `TestRequeueCommandInterface` (each `run`).

## Where to change
- `src/vibey/cli/test_harness.py` and `src/vibey/cli/interfaces/test_harness_interface.py` (with `edit_file`).
- `tests/cli/test_test_harness_cli.py` (tests appended; imports into its import block).

## Acceptance criteria
- [ ] `status` shows a holder, running attempts and recent answers from a seeded in-memory store, and `--json` parses.
- [ ] `dead-letters` lists only unanswered letters by default and all with `--all`, and counts malformed messages.
- [ ] `requeue` answers the letter once, submits a granted request, and exits with the answer's code; a second requeue exits 2.
- [ ] 100% coverage of `src/vibey/cli/`.

## Tests to write first (TDD)
Appended to `tests/cli/test_test_harness_cli.py`. Every test invokes `th_cli.test_app` through
`CliRunner` with `obj=<Command>(composition_factory=lambda *a, **k: comp)`, where `comp` is an
`InMemoryTestHarnessComposition` (`tests/fakes/harness_composition.py`) seeded through its
store (`begin`, `finish`, `put_answer`, `dead_letter`, `put_malformed`) and its lock
(`InMemoryMachineLock.seize(holder)`, lane fakes-test-harness):
- `test_status_text_and_json`
- `test_status_without_a_holder`
- `test_dead_letters_default_and_all`
- `test_dead_letters_counts_malformed`
- `test_requeue_grants_once` (the composition's `ScriptedHarnessClient.submitted[0].grant` is `True`, and the store now says answered)
- `test_requeue_unknown_and_answered_exit_2`
- `test_requeue_warns_on_missing_env_and_a_new_key`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- A cancel command: ADR-0045 §11 stops a run with `kill <pid>`, which `status` prints.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T15-test-run-cli.
- **Files touched:** `src/vibey/cli/test_harness.py`, `src/vibey/cli/interfaces/test_harness_interface.py`, `tests/cli/test_test_harness_cli.py`.
- **Shares a file with:** `cli/test_harness.py` (harness-T15 before, harness-T25 after).
- **Must keep passing unchanged:** harness-T15b's and T15's tests, `tests/cli/*`, and the protected tests.
- **Registry (amendment A4):** nothing new.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Substitute only at a declared seam (`obj=` and constructor keywords). Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; `setenv` and `delenv` are allowed.
  - Default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out).
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
