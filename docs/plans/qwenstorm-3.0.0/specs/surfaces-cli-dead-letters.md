## Title
feat(cli): vibey surface dead-letters lists parked operations from PostgreSQL, and vibey surface requeue grants one

## Why
Draft ADR-0047 §9 (`specs/ADR-surface-lanes.md`): "**Seeing them.** `vibey surface dead-letters
[--surface NAME] [--json]` (lane S28) reads PostgreSQL, so it works while a lane is down."
"**The grant.** `vibey surface requeue <id>` republishes a retained request with `grant: true` …
A request that is not retained … cannot be requeued from its row, and the command says so and
names the caller as the only place the value exists." Doctrine 7: the human reading comes
first, and `--json` is the machine reading of the same result (the pattern of
`src/vibey/cli/ledger_search.py:1-12`). The requeue logic is `surfaces-requeue`'s; this lane is
its thin command. ADR-0047 lane S28.

## Required behaviour
Append to `src/vibey/cli/surface.py` (lane `surfaces-cli-serve-ping`):

1. `SurfacePresenter` gains:
   - `dead_letter_line(record) -> str`:
     `<id> <dead_lettered_at %Y-%m-%d %H:%M:%S> <surface>.<operation> reason=<reason> op=<op_id> attempts=<n> retained=<yes|no>`,
     plus ` answered <answered_at> by <answered_by>` when answered;
   - `dead_letters_human(records) -> list[str]`: the lines, then
     `N parked operation(s)` (or `no parked operations`);
   - `dead_letters_json(records) -> str`: one JSON document, `{"dead_letters": [...]}`, every
     column of every row, `request` included as stored (already redacted).
2. `class SurfaceDeadLettersCommand`:
   `async run(self, *, surface: str | None, include_answered: bool, limit: int, as_json: bool) -> int`:
   `surface` goes through `CATALOGUE.parse_surface` (a bad name is `typer.BadParameter`, exit 2)
   **before** anything is opened; then `async with CliComposition.current().open_app() as resources:`
   `records = await resources.surface_dead_letters.recent(surface=…, include_answered=…, limit=…)`;
   print; return 0.
3. `class SurfaceRequeueCommand`:
   `async run(self, dead_letter_id: UUID, *, answered_by: str) -> int`: opens the app, builds
   the composition through the seam (`CliComposition.current().surface_composition(...)`), and
   builds `SurfaceRequeuer(dead_letters=resources.surface_dead_letters, client=<the composition's AMQP client for requests>, topology=…, names=…, settings=…, recorder=SurfaceLedgerRecorder(ledger=resources.ledger, projects=resources.projects, …), clock=SystemClock())`.
   To reach the AMQP client, `SurfaceComposition` gains `requeuer(self, resources) -> SurfaceRequeuerInterface`
   (in `bootstrap.py`, with its interface line), so the command holds no wiring. On success it
   prints `granted <surface>.<operation> (op <op_id>) as request <request_id>` and returns 0; a
   `RequeueRefused` prints its reason to stderr and returns 1; `SurfaceTransportNotConfigured`
   prints its message and returns 1.
   `answered_by` defaults to the `--by` option, else `os.environ.get("USER")`, else `"operator"`.
4. Typer functions `surface_dead_letters(surface: str | None = --surface, include_answered: bool = --all, limit: int = --limit/-n (default 100, 1–1000), as_json: bool = --json)`
   and `surface_requeue(dead_letter_id: UUID, answered_by: str | None = --by)`, registered in
   `cli/main.py` beside `serve` and `ping` as `dead-letters` and `requeue`.
5. Interfaces for the two commands in `src/vibey/cli/interfaces/surface_interface.py`, and the
   presenter interface gains the three methods.

## Where to change
- `src/vibey/cli/surface.py`, `src/vibey/cli/interfaces/surface_interface.py`,
  `src/vibey/cli/main.py` (two registration lines), `src/vibey/bootstrap.py` and
  `src/vibey/bootstrap_interface.py` (`SurfaceComposition.requeuer`).
- New `tests/cli/test_surface_dead_letters_cli.py`.

## Acceptance criteria
- [ ] With rows seeded in `InMemoryApp`'s `surface_dead_letters`, `vibey surface dead-letters` prints one line per open row, newest first, and the count; `--all` includes answered rows; `--surface email` filters; `--json` is one parseable document holding every column.
- [ ] `--surface bus` exits 2 with the exemption sentence, before any app is opened.
- [ ] `vibey surface requeue <id>` on a retained row publishes one grant to the in-memory broker, marks the row answered by `--by`, prints the new request id, exits 0.
- [ ] A not-retained, unknown or already-answered id exits 1 with the requeuer's message on stderr; nothing is published.
- [ ] No test patches an import; 100% `cli/` branch coverage.

## Tests to write first (TDD)
`tests/cli/test_surface_dead_letters_cli.py` (no service; `CliRunner.invoke(..., obj=CliComposition(open_app=InMemoryApp(...).open_app, surface_composition=<factory over InMemoryAmqpClient>))`):
- `test_dead_letters_lists_open_rows_newest_first`
- `test_all_includes_answered_rows`
- `test_surface_filter_and_the_bus_refusal`
- `test_dead_letters_json_is_one_document`
- `test_requeue_grants_a_retained_row`
- `test_requeue_refusals_exit_one` (parametrized)
- `test_the_commands_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/cli/test_surface_dead_letters_cli.py tests/cli/test_surface_cli.py tests/fakes tests/meta
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider tests/cli tests/test_bootstrap_surfaces.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- Pruning answered rows (a follow-up the ADR names). `docs/reference/cli.md`
  (`surfaces-docs-wave`). CHANGELOG.md, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
  Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `surfaces-cli-serve-ping`, `surfaces-requeue`, `surfaces-app-records`.
- **Shares a file with:** `src/vibey/cli/surface.py`, `src/vibey/cli/main.py`, `src/vibey/bootstrap.py`.
- **Must keep passing unchanged:** `tests/cli/*`, `tests/test_bootstrap_surfaces.py`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file. `main.py` and `bootstrap.py` are long: `edit_file` only.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol in `cli/interfaces/`.
  - Substitute only at a declared seam (`CliRunner.invoke(obj=...)`); never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - Never block a worker on a human; the commands only read and publish.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
