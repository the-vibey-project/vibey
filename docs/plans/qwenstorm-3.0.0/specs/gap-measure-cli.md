## Title
feat(cli): vibey measure shows recorded measurements with their object, source and cutoff, and ingests measurement logs

## Why
Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`): measurements "are published
with the decisions they drive (10.f)". 10.f (`:419`): every claim "is tied to observable …
evidence whose scope and cutoff are stated", and missing evidence "is reported" as unknown. An
operator has no way to read the measurements the `gap-measure-*` lanes record, and nothing moves
the measurement logs (lanes `gap-measure-gh-2`, `gap-measure-test-runs`) into the ledger. This
lane adds `vibey measure show` and `vibey measure ingest`, following the command-class pattern of
`src/vibey/cli/ledger_search.py:145-287` (logic in a class; thin typer functions with the reason
comment of `:275-276`), with a header built in the evidence-bounded status vocabulary (lane
`gap-status-vocabulary`).

## Required behaviour
1. New `src/vibey/cli/measure.py`:
   - `class MeasurementPresenter` with `header(...)` and `lines(measurements)`:
     - the header is exactly four lines:
       `object: measurements (kind: <kind or "any">, name: <name or "any">)`;
       `source: MeasurementRecorded events in the ledger of <fleet id> (fleet)` plus
       `f" and of {project}"` when `--project` is given;
       `cutoff: newest measurement ended <ISO> ; read at <ISO now>` (or
       `cutoff: none recorded ; read at <ISO now>`);
       `state: measured (<n> shown[, <u> unreadable][, older ones cut by --limit])` or
       `state: unknown (no measurement recorded)`. Build these through
       `gap-status-vocabulary`'s status type (its object, source, cutoff and state fields) and
       render them with this exact text;
     - one line per measurement:
       `f"{ended_at.isoformat()} {kind} {name} {outcome}"` then `f" {metric}={value:g}"` per
       reading, then `f" ({detail})"` when `detail` is non-empty.
   - `class MeasureCommand`, `__init__(self, *, presenter: MeasurementPresenterInterface = PRESENTER,
     open_app: Callable[[], AbstractAsyncContextManager[AppResourcesInterface]] = build_app,
     ingester: Callable[[MeasurementPort, Clock], MeasurementLogIngesterInterface] | None = None,
     harness_log: Callable[[], Path | None] | None = None)`:
     - `async def show(self, *, kind: str | None, name: str | None, project: UUID | None,
       limit: int, as_json: bool) -> None`: `kind` must be a `SubjectKind` value, else
       `typer.BadParameter`. Inside `open_app()`: for the fleet id
       (`resources.measure.fleet_project_id`) and `project` when given,
       `await resources.ledger_search.search(pid, LedgerQuery(kinds=frozenset({EventKind.MEASUREMENT_RECORDED}), limit=limit))`;
       each event's payload through `MEASUREMENT_CODEC.decode` (a `MalformedMeasurement` counts
       as unreadable); filter by kind and name; `MEASUREMENT_SERIES.unique`; newest `ended_at`
       first; at most `limit`. Prints the header then the lines; `--json` prints one object
       `{"object", "source", "cutoff", "state", "measurements": [<stored payloads>]}`.
     - `async def ingest(self, logs: list[Path]) -> int`: the logs are `logs`, or, when empty,
       `resources.measure.logs` plus `harness_log()` when it returns an existing path. Each
       relative path resolves against the working directory. For each: a missing file prints
       `f"{path}: no log"`; otherwise `report = await ingester(resources.measurements,
       resources.clock).ingest(path)` and prints `f"{path}: read {report.read}, recorded
       {report.recorded}, already ingested {report.skipped}"`, each malformed entry to stderr;
       a `ValueError` prints `f"vibey measure ingest: {exc}"` to stderr and goes on to the next
       log. Returns 1 when any log failed or held malformed records, else 0.
     - The default `ingester` is `lambda port, clock: MeasurementLogIngester(port, clock=clock)`
       (lane `gap-measure-log-ingest`); the default `harness_log` returns
       `TestHarnessSettings.from_sources(config, os.environ).state_dir / "measurements.jsonl"`
       (lane T05), with `config` loaded from `vibey.toml` when it exists, and `None` when
       `from_sources` raises `ConfigError`.
   - `MEASURE: Final[MeasureCommandInterface] = MeasureCommand()`.
   - typer functions `measure_show(ctx: typer.Context, kind, name, project, limit, as_json)` and
     `measure_ingest(ctx: typer.Context, log: list[Path] | None)`, each using
     `command = ctx.obj if isinstance(ctx.obj, MeasureCommandInterface) else MEASURE` (the
     declared seam), with the reason comment copied from `ledger_search.py:275-276`;
     `measure_ingest` raises `typer.Exit(code)` with the code `ingest` returned.
2. New `src/vibey/cli/interfaces/measure_interface.py`: `MeasurementPresenterInterface`,
   `MeasureCommandInterface`.
3. `src/vibey/cli/main.py` beside `:86-90`: `measure_app = typer.Typer(name="measure",
   invoke_without_command=True)`, `app.add_typer(measure_app, name="measure")`,
   `measure_app.command("show")(measure_show)`, `measure_app.command("ingest")(measure_ingest)`.

## Where to change
- New `src/vibey/cli/measure.py`, `src/vibey/cli/interfaces/measure_interface.py`;
  `src/vibey/cli/main.py` (imports beside `:38`, registration beside `:86-90`).
- New `tests/cli/test_measure_cli.py`: resources are a small frozen dataclass with
  `ledger_search=InMemoryLedgerSearch(ledger)` (`tests/fakes/ledger_publication.py`, lane
  `fakes-ledger-publication`), `measure=MeasureConfig(...)`, `measurements=InMemoryMeasurements()`
  and `clock=FakeClock(...)`, opened by an `asynccontextmanager`; measurements are put in the
  ledger through `LedgerMeasurementSink(ledger, InMemoryFleetLedgerProject())`; the CLI is
  driven with `CliRunner().invoke(app, [...], obj=MeasureCommand(open_app=...))`.

## Acceptance criteria
- [ ] With three fleet measurements (two `queue`, one `surface`), `vibey measure show --kind queue`
      prints the four header lines with `state: measured (2 shown)` and two lines, newest first.
- [ ] With none, it prints `state: unknown (no measurement recorded)` and exits 0.
- [ ] A payload with an unknown `readings` value type is counted `1 unreadable`.
- [ ] `--kind satellite` exits 2 naming the allowed kinds.
- [ ] `vibey measure ingest --log <good> --log <rewritten>` ingests the first, prints the second's
      error on stderr and exits 1; with no `--log`, the configured logs and the harness log are
      used, and a missing one prints `no log`.
- [ ] 100% branch coverage of `src/vibey/cli/`.

## Tests to write first (TDD)
`tests/cli/test_measure_cli.py`:
- `test_show_prints_the_evidence_header_and_the_newest_measurements`
- `test_show_says_unknown_when_nothing_was_recorded`
- `test_show_counts_unreadable_payloads`
- `test_show_reads_a_named_project_as_well_as_the_fleet`
- `test_show_json_is_one_document`
- `test_an_unknown_kind_is_a_usage_error`
- `test_ingest_reports_each_log_and_fails_on_a_rewritten_one`
- `test_ingest_defaults_to_the_configured_and_harness_logs`
- `test_the_command_and_presenter_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli/test_measure_cli.py tests/cli/test_main.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- `docs/reference/cli.md` (the docs wave); publishing measurements to the public site (the
  allowlist is `gap-measure-domain`'s; the site is `vibey ledger site`'s); acting on
  measurements (gap D2, another writer's).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(cli): vibey measure shows recorded measurements with their object, source and cutoff, and ingests measurement logs`. Do not push.

## Lane card
- **Depends on:** `gap-measure-log-ingest`, `gap-measure-test-runs`, `gap-status-vocabulary`,
  `orm-app-resources` (`resources.ledger_search`), `fakes-ledger-publication`,
  `harness-T05-test-harness-config`.
- **Shares a file with:** `cli/main.py` (registration lines only).
- **Must keep passing unchanged:** every test under `tests/cli/` and the protected tests.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
