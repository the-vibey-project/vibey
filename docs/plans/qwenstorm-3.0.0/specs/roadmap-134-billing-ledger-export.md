## Title
feat(ledger): `vibey ledger export --billing` writes the billing ledger `vibey-gh forecast` reads, and the round trip is proven

## Why
Issue #134, "Proposed child issues" 6, and issue #88, "Proposed child issues" 1: one lane
(rewrites `issue-audit/updates/134.md` and `issue-audit/updates/88.md`). This is cost
*accounting*, what a run cost vibey. Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`)
says nothing runs unmeasured, and 10.f (`doctrines.md:419`) keeps unknown as unknown. So the
published forecast says `source problem: billing ledger unavailable at .vibey/billing-ledger.jsonl`
(`docs/estimate.md:19`), and every billing dimension reads `unknown`.

The projection already exists. `vibey ledger export PROJECT --out FILE --billing`
(`src/vibey/cli/ledger_publication.py:200-222`, flag at `:211-217`) applies `BILLING_POLICY`
(`src/vibey/domain/publication_policy.py:392-410`). It keeps `TurnCompleted.cost_usd`,
`BudgetSpent.dollars/turns` and the counted kinds. It also writes the shard format that
`BillingLedgerReader` reads (`src/vibey_tools/gh/vibey_gh/estimate_ledger.py:51-156`). The reader skips
every `{"shard": …}` header line (`:72-73`) and sums `kind`, `payload` and `produced_at`, the
fields `LedgerLines` writes. But nothing puts the file where the forecast looks:
- `vibey-gh forecast` reads `[estimate.forecast] billing_ledger` (`.vibey-gh.toml:211`; default
  `.vibey/billing-ledger.jsonl`, `vibey_gh/config.py:1355`, parsed at `:1444-1446`). A relative
  path resolves against the vibey-gh root (`vibey_gh/cli.py:841-845`).
- `--out` is required (`ledger_publication.py:202-210`).
- The only billing test checks payloads (`tests/cli/test_ledger_publication_cli.py:222-276`).
  Nothing reads the file back through vibey-gh's reader.

12.c (`doctrines.md:455`) and 10.e (`:417`): one key, read by both sides. The conductor reads
vibey-gh's own key through vibey-gh's own loader, `vibey_gh.config.load_config`
(`config.py:1690`). vibey may import vibey-gh (ADR-0017; `.importlinter` names `vibey_gh` a root
package, and `src/vibey/infrastructure/preflight_feasibility.py:15-25` already does). The lane
extends `export` instead of adding a subcommand: `--billing` already selects the projection on
`export`, and only its destination is missing. A new subcommand would copy the command class,
its presenter and its seam.

A project's `repo_path` is unique (`migrations/0001_project.sql:18`). But two projects in
sub-directories of one repository resolve to one vibey-gh root (`find_root`,
`vibey_gh/config.py:1630-1647`). So the default path must never silently replace another
project's billing ledger (10.f).

## Required behaviour
1. In `src/vibey/cli/ledger_publication.py`, after `SITE_WRITER` (`:68`), add:
   ```python
   class ForecastBillingLocation:
       """Where `vibey-gh forecast` reads a repository's billing ledger: the
       `[estimate.forecast] billing_ledger` key of that repository's `.vibey-gh.toml`
       (vibey-gh's default `.vibey/billing-ledger.jsonl`), resolved against the vibey-gh
       root that holds `repo_path` -- the resolution the forecast applies
       (`vibey_gh/cli.py:841-845`). One key, read by both sides (12.c, 10.e)."""

       def resolve(self, repo_path: Path) -> Path:
           config = load_config(repo_path)
           configured = Path(config.estimate.forecast_billing_ledger)
           return configured if configured.is_absolute() else config.root / configured


   FORECAST_BILLING_LOCATION: Final[ForecastBillingLocationInterface] = ForecastBillingLocation()
   """Where `--billing` writes when `--out` is not given. Annotated with the interface so
   `mypy --strict` checks the class against its declared seam."""
   ```
   Import `from vibey_gh.config import load_config`. Then run
   `uv run ruff check --fix src/vibey/cli/ledger_publication.py`, which puts the import in the
   third-party block after `import typer`, where `preflight_feasibility.py:15-25` keeps its
   `vibey_gh` imports.
2. `LedgerExportCommand.__init__` (`:127-142`) gains a last keyword parameter
   `billing_location: ForecastBillingLocationInterface = FORECAST_BILLING_LOCATION`, stored as
   `self._billing_location`.
3. `LedgerExportCommand.run(self, project_id: UUID, out: Path | None, *, billing: bool = False) -> None`:
   - First, before opening the app: if `out is None and not billing`, then
     `raise typer.BadParameter("the public shard has no default path; pass --out FILE (only --billing defaults, to the billing ledger vibey-gh forecast reads)", param_hint="--out")`.
     This is a usage error, exit 2. Copy the comment at `:175`.
   - The unknown-project check is unchanged (`:146-149`).
   - `target = out if out is not None else self._forecast_ledger(project.project_id, project.repo_path)`.
     `target` replaces `out` in the `exporter.export(...)` call and in `self._presenter.exported(shard, …)`.
     Nothing else in `run` changes.
4. New method `_forecast_ledger(self, project_id: UUID, repo_path: Path) -> Path`:
   - `path = self._billing_location.resolve(repo_path)`. If that raises
     `(OSError, ValueError, TypeError)` as `exc`, echo
     `f"cannot find the forecast's billing ledger for {repo_path}: {exc}"` and
     `raise typer.Exit(1) from exc`. A malformed `.vibey-gh.toml` raises `TOMLDecodeError`,
     which is a `ValueError`.
   - `holder = self._store.read(path).header.project_id`. If that raises
     `InvalidLedgerShard` (already imported, `:40`), return `path`: there is no file, or the
     file is not a shard, so it is replaced, as `--out` replaces.
   - If `holder != project_id`, echo
     `f"{path} holds the billing ledger of project {holder}; pass --out to write project {project_id}'s billing elsewhere"`
     and `raise typer.Exit(1)`. Otherwise return `path`, so re-exporting the same project
     replaces its own file.
   - Docstring: "The forecast's billing ledger for this project's repository, unless it holds
     another project's billing: replacing that would drop its spend from the forecast without
     a word (10.f)."
5. `ledger_export` (`:200-222`): `out` becomes
   `Annotated[Path | None, typer.Option("--out", "-o", dir_okay=False, help="The shard file to write (JSON Lines). Replaced if it exists. Required for the public shard; with --billing it defaults to the billing ledger vibey-gh forecast reads ([estimate.forecast] billing_ledger in the repository's .vibey-gh.toml, default .vibey/billing-ledger.jsonl).")] = None`.
   The docstring becomes "Write a project's public shard, or the operator billing projection,
   by default where vibey-gh forecast reads it." The body is unchanged.
6. `src/vibey/cli/interfaces/ledger_publication_interface.py`:
   - `LedgerExportCommandInterface.run(self, project_id: UUID, out: Path | None, *, billing: bool = False) -> None`,
     with the docstring "A usage error without --out unless billing; exit 1 for an unknown
     project, an unreadable billing location, or a billing ledger that holds another project."
   - Add `@runtime_checkable class ForecastBillingLocationInterface(Protocol)` with
     `def resolve(self, repo_path: Path) -> Path:` and the docstring "Where vibey-gh forecast
     reads the billing ledger of the repository that holds repo_path."
   - Export it from `src/vibey/cli/interfaces/__init__.py`, in the import at `:5-9` and in
     `__all__`, in sorted order.
7. The `BILLING_POLICY` allowlist is unchanged here. Carrying the local lane's timings is
   `roadmap-134-cost-integral-p1`.

## Where to change
- `src/vibey/cli/ledger_publication.py` (use `edit_file`; the file is 252 lines).
- `src/vibey/cli/interfaces/ledger_publication_interface.py`, `src/vibey/cli/interfaces/__init__.py`.
- New `tests/cli/test_billing_ledger_export.py`. Line 1 is the provenance header, copied
  byte-for-byte from `tests/cli/test_ledger_publication_cli.py:1`.
- The tests run on the in-memory app. Use `InMemoryApp` from `tests/fakes/app.py` (lane
  `fakes-bootstrap-seam`) and seed it through `async with app.open_app() as resources:`, as
  `tests/cli/ops_support.py` does (lane `fakes-cli-operational-1`). Pass `app.open_app` to
  `LedgerExportCommand(open_app=...)`, the declared seam (`:134`). The ledger is
  `InMemoryLedger` (lane `fakes-ledger`). Patch nothing.
- No other file. `tests/cli/test_ledger_publication_cli.py` is not edited: its calls pass `out`
  positionally and keep working.

## Acceptance criteria
- [ ] `vibey ledger export PID --billing` in a repository with a `.vibey-gh.toml` writes
      `.vibey/billing-ledger.jsonl` there. `BillingLedgerReader().read(...)` gives
      `problems == ()`, `dollars == 4.0`, `turn_completed_events == 1`, `budget_turns == 3`,
      `phase_transition_events == 2`, `ledger_events == 4` and `elapsed_seconds == 180.0` for
      the seeded ledger below.
- [ ] Those dollars equal `LedgerBudgetSource(ledger).current(pid, 1).dollars_spent`: the
      forecast's billing agrees with `vibey cost` (`src/vibey/cli/main.py:832-892`,
      `application/budget_source.py:94-109`).
- [ ] `[estimate.forecast] billing_ledger = "ledger/billing.jsonl"` moves the file there.
- [ ] A billing ledger that holds another project is never replaced (exit 1, file unchanged).
- [ ] `vibey ledger export PID` without `--out` exits 2, naming `--out`.
- [ ] 100% branch coverage of `src/vibey/cli/`.

## Tests to write first (TDD)
`tests/cli/test_billing_ledger_export.py` (default tier). Helpers:
- `T0 = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)`.
- `_drafts(pid)` returns five `LedgerEventDraft`s (`vibey.infrastructure.engines.tailer`),
  cycle 1, each with `digest=digest_event(payload)` and `correlation_id=uuid4()`:
  1. `PHASE_TRANSITIONED`, phase `DESIGN`, `T0`, payload `{"from": "intake", "to": "design", "cycle": 1}`, `TRUSTED`.
  2. `BUDGET_SPENT`, `DESIGN`, `T0+60s`, engine `CLAUDELOOP`, payload `{"dollars": 1.5, "turns": 3}`, `TRUSTED`.
  3. `PHASE_TRANSITIONED`, `BUILD`, `T0+120s`, payload `{"from": "design", "to": "build", "cycle": 1}`, `TRUSTED`.
  4. `TURN_COMPLETED`, `BUILD`, `T0+180s`, engine `CLAUDELOOP`, payload `{"cost_usd": 2.5, "text": "private output"}`, `AGENT`.
  5. `DECISION_RECORDED`, `BUILD`, `T0+240s`, payload `{"decision_id": "d1", "title": "use Postgres"}`, `TRUSTED`.
- `_seed(app, repo_path) -> UUID` creates the project
  (`resources.projects.create("billing", repo_path, max_cycles=3, config={})`) and appends the
  five drafts.

Tests:
- `test_billing_export_writes_the_forecast_billing_ledger_by_default`: `repo/.vibey-gh.toml` is
  empty. After `run(pid, None, billing=True)`, `repo/.vibey/billing-ledger.jsonl` exists,
  stdout starts with `exported 4 of 5 ledger event(s)`, and `"private output"` is not in the
  file text.
- `test_the_billing_ledger_round_trips_through_vibey_gh_reader`: every number in the first
  acceptance criterion, read with `from vibey_gh.estimate_ledger import BillingLedgerReader`,
  plus the reconciliation with `LedgerBudgetSource` over `resources.ledger`
  (`dollars_spent == 4.0`, `turns_spent == 4`).
- `test_the_configured_billing_ledger_path_is_honoured`: the file lands at
  `repo/ledger/billing.jsonl`, and `repo/.vibey/billing-ledger.jsonl` does not exist.
- `test_an_absolute_configured_path_is_used_as_is`:
  `ForecastBillingLocation().resolve(repo) == absolute` when the key names `str(absolute)`.
- `test_an_explicit_out_wins_over_the_forecast_path`: `run(pid, tmp_path / "x.jsonl", billing=True)`
  writes `x.jsonl`. The default path is not created.
- `test_re_exporting_the_same_project_replaces_its_billing_ledger`: two exports both succeed.
  The file holds exactly one line containing `"shard"`.
- `test_another_projects_billing_ledger_is_never_replaced`: `repo/.vibey-gh.toml` is empty.
  Projects A at `repo / "a"` and B at `repo / "b"` share that root. Export A. Exporting B
  raises `typer.Exit` with `exit_code == 1`, stdout names A's id with `holds the billing ledger of project`,
  and `JsonlShardStore().read(path).header.project_id == A`.
- `test_an_unreadable_forecast_configuration_exits_1`: `.vibey-gh.toml` is `x = [\n`. The run
  raises `typer.Exit(1)`, and stdout contains `cannot find the forecast's billing ledger`.
- `test_the_public_shard_still_needs_out`:
  `CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"}).invoke(app, ["ledger", "export", str(uuid4())])`
  exits 2, and `"pass --out FILE"` is in `result.output`. No app is opened: the check runs first.
- `test_the_location_and_command_satisfy_their_seams`:
  `isinstance(FORECAST_BILLING_LOCATION, ForecastBillingLocationInterface)` and
  `isinstance(LEDGER_EXPORT, LedgerExportCommandInterface)`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli/test_billing_ledger_export.py tests/domain/test_publication_policy.py
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    uv run pytest -q -p no:cacheprovider tests/cli/test_ledger_publication_cli.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- Committing `.vibey/billing-ledger.jsonl`, which is the operator's act, and the
  delivery-estimate workflow.
- The local lane's timing fields in the billing projection (`roadmap-134-cost-integral-p1`) and
  any change to vibey-gh's reader (`roadmap-134-cost-integral-p2`).
- Aggregating several projects into one billing ledger. Customer billing, prices and invoices
  belong to #86 and #88; this is cost accounting only.
- `docs/reference/cli.md`, CHANGELOG. Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
