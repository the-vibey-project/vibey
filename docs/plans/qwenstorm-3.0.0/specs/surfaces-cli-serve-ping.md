## Title
feat(cli): vibey surface serve runs one lane or all of them, and vibey surface ping asks each lane who it is

## Why
Draft ADR-0047 §12 and "Migration" (`specs/ADR-surface-lanes.md`): `vibey surface serve <name>`
is the lane process (the chart runs `args: ["surface", "serve", "<name>"]`, §14); on a laptop
"run `vibey surface serve --all`"; "`vibey surface serve bus` exits 2 with this paragraph's
first sentence" (§11); and cluster-smoke asks `vibey surface ping --all` "from inside the
worker pod" (§14). Every caller-side error names `vibey surface serve <name>` as the remedy
(§6). CLI commands reach the app through `CliComposition` (lane `fakes-job-wakeup`), so tests
substitute with `CliRunner.invoke(obj=...)`, never by patching (9.b). The typer function bodies
are the only module-level functions, holding no logic, as `cli/ledger_search.py:233-287` does
(ADR "non-negotiable 10"). Part of ADR-0047 lanes S27–S28.

## Required behaviour
1. **`src/vibey/cli/surface.py`** (new):
   - `class SurfacePresenter`: `ping_line(surface, answer: Mapping[str, object] | None, error: str | None) -> str`
     → `surface <name>: ok instance=<instance> backend=<backend> since=<started_at>` or
     `surface <name>: unavailable (<error>)`; `ping_json(results) -> str` (one JSON document:
     `{"<name>": {"ok": bool, …}}`).
   - `class SurfaceServeCommand`: `names(self, name: str | None, all_: bool) -> tuple[SurfaceName, ...]`
     — exactly one of `name` / `--all`, else `typer.BadParameter` (exit 2); `name` goes through
     `CATALOGUE.parse_surface`, whose `ValueError` (the bus's `BUS_EXEMPT_MESSAGE`, or an
     unknown name) becomes `typer.BadParameter` (exit 2). `async run(self, names, stop: asyncio.Event) -> int`:
     `async with CliComposition.current().open_app() as resources:` build
     `composition = CliComposition.current().surface_composition(config=<resolved config>, environ=os.environ, clock=SystemClock(), logger=…)` (behaviour 5),
     one `composition.host(name, resources)` per surface, run them all as tasks with the same
     `stop`, and return the highest exit code (3 when any lost its lease). `aclose()` in
     `finally`. SIGTERM and SIGINT set `stop` (use the loop's `add_signal_handler`, as the worker
     does).
   - `class SurfacePingCommand`: `async run(self, names, *, as_json: bool) -> int`: builds a
     composition the same way (behaviour 5) from configuration and environment (no database needed), and for each
     surface `await composition.lane_client().ping(name)` under the lane client's own bounds;
     `SurfaceLaneUnavailable` or `SurfaceTransportNotConfigured` is that surface's `error`.
     Prints one line per surface (or the JSON), returns 0 when all answered, else 1.
   - `PRESENTER`, `SERVE`, `PING`: module constants annotated with their interfaces.
   - Typer functions `surface_serve(name: Annotated[str | None, typer.Argument()] = None, all_: Annotated[bool, typer.Option("--all")] = False) -> None`
     and `surface_ping(name=None, all_=False, as_json: Annotated[bool, typer.Option("--json")] = False) -> None`,
     each with the one-line reason comment `ledger_search` carries, raising `typer.Exit(code)`.
2. **`src/vibey/cli/interfaces/surface_interface.py`** (new): `SurfacePresenterInterface`,
   `SurfaceServeCommandInterface`, `SurfacePingCommandInterface`, exported from
   `src/vibey/cli/interfaces/__init__.py`.
3. **`src/vibey/cli/main.py`**: after the `ledger_app` registration lines (`:86-90`), add
   `surface_app = typer.Typer(name="surface", no_args_is_help=True)`,
   `app.add_typer(surface_app, name="surface")`, `surface_app.command("serve")(surface_serve)`,
   `surface_app.command("ping")(surface_ping)`, and the import.
4. The composition's configuration is resolved as `build_app` resolves it (file, then
   environment; lane `surfaces-env`); reuse that function, do not copy it.
5. **The seam.** `CliComposition` (`src/vibey/cli/composition.py`, lane `fakes-job-wakeup`)
   gains the keyword field `surface_composition: Callable[..., SurfaceCompositionInterface] = SurfaceComposition`,
   mirrored in `CliCompositionInterface`. Both commands build their composition only through
   `CliComposition.current().surface_composition(config=…, environ=…, clock=…, logger=…)`, so a
   test passes a factory that injects `amqp_factory=` and `leases_factory=`.

## Where to change
- New `src/vibey/cli/surface.py`, `src/vibey/cli/interfaces/surface_interface.py`;
  `src/vibey/cli/interfaces/__init__.py`; `src/vibey/cli/main.py` (registration lines only);
  `src/vibey/cli/composition.py` and `src/vibey/cli/interfaces/composition_interface.py` (one field).
- New `tests/cli/test_surface_cli.py`.

## Acceptance criteria
- [ ] `vibey surface serve bus` exits 2 and prints the bus-exemption sentence; `vibey surface serve nope` exits 2 listing the eleven names; `serve` with both a name and `--all`, or neither, exits 2.
- [ ] `vibey surface serve tracker`, invoked with a `CliComposition` over `InMemoryApp` and a `SurfaceComposition` built on a shared `InMemoryAmqpClient`/`InMemoryAmqpLeases` (inject through the composition object the test passes in `obj=`), serves a queued call and exits 0 when stopped.
- [ ] `vibey surface ping --all` prints eleven `ok` lines and exits 0 against running in-memory hosts; with one host stopped it prints that surface `unavailable` and exits 1; `--json` prints one parseable document.
- [ ] `ping` with `direct` transport and no URL prints each surface unavailable with the `SurfaceTransportNotConfigured` remedy and exits 1.
- [ ] No test patches an import; the ratchet does not rise; 100% `cli/` branch coverage.

## Tests to write first (TDD)
`tests/cli/test_surface_cli.py` (no service; `CliRunner.invoke(app, [...], obj=CliComposition(...))`, `InMemoryApp`, in-memory broker and leases; ping hosts are started as tasks in the test and stopped at the end):
- `test_serving_the_bus_is_refused_with_the_exemption`
- `test_serve_needs_exactly_one_name_or_all`
- `test_serve_runs_a_lane_until_stopped`
- `test_ping_all_reports_every_lane`
- `test_ping_reports_an_unavailable_lane_and_exits_one`
- `test_ping_json_is_one_document`
- `test_ping_without_a_bus_names_the_remedy`
- `test_the_commands_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/cli/test_surface_cli.py tests/fakes tests/meta
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- `dead-letters` and `requeue` (`surfaces-cli-dead-letters`); the chart
  (`surfaces-chart-lane-deployments`). `docs/reference/cli.md` (`surfaces-docs-wave`).
  CHANGELOG.md, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Do not push, open PRs
  or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `surfaces-composition`, `fakes-job-wakeup` (`CliComposition`), `fakes-bootstrap-seam` (`InMemoryApp`).
- **Shares a file with:** `src/vibey/cli/main.py` (T15, R02, R17, R27, R28, R33 edit other parts; add only the registration lines), `src/vibey/cli/interfaces/__init__.py`.
- **Must keep passing unchanged:** `tests/cli/*`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file. `main.py` is long: `edit_file` only; keep `SIGTERM_LATCH.arm()` first.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol in `cli/interfaces/`; the typer functions hold no logic and say why they are module-level.
  - Substitute only at a declared seam (`CliRunner.invoke(obj=...)`); never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no service.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
