## Title
feat(cli): `--engines paid-ide` resolves to `vscode-paid`, and the worker says so aloud

## Why
Lane `gap-paid-ide-default-1` resolves the unnamed paid-IDE declaration `paid-ide` in
`vibey.toml`, per 8.b's paid defaults (`src/vibey_tools/gh/docs/doctrines.md:188-194`). The
command line parses engine lists in two other places, each by calling `EngineId(...)` on every
comma-separated item, so `paid-ide` would be refused there:
- `vibey worker --engines` (`src/vibey/cli/main.py:1471-1477`);
- the in-cluster preflight's engine-auth check, which takes the worker's `--engines` verbatim
  (`src/vibey/infrastructure/cluster_preflight.py:168-170`, reached from
  `vibey doctor --cluster --engines`, `main.py:1212-1219`).
Two copies of one parse is how they drift. This lane gives the parse one pure class in the
domain and uses it at both sites. 8.b also requires a paid declaration to be made aloud, so
the worker prints the resolution.

`vibey doctor` (without `--cluster`) reads no project configuration (`main.py:1186-1391`), so
it has no declaration to announce; the worker is where the pool is chosen.

## Required behaviour
1. New `src/vibey/domain/engine_allow_list.py` (provenance line 1, copied from
   `src/vibey/domain/engine.py:1`), pure:
   - `@dataclass(frozen=True, slots=True) class EngineAllowList` with
     `engines: frozenset[EngineId] | None` and `resolved: tuple[tuple[str, str], ...]`.
   - `class EngineAllowListParser` with
     `parse(self, value: str | None) -> EngineAllowList`: `None` or an all-blank value gives
     `EngineAllowList(None, ())`. Otherwise split on `,`, strip each item, drop empty items,
     resolve with `PAID_IDE_RESOLVER.resolve(...)` (lane `-1`), then build
     `frozenset(EngineId(item) for item in resolved_items)`. An unknown id raises the same
     `ValueError` `EngineId(...)` raises today.
   - `ENGINE_ALLOW_LIST_PARSER: Final[EngineAllowListParserInterface] = EngineAllowListParser()`.
2. New `src/vibey/domain/interfaces/engine_allow_list_interface.py` (provenance line 1)
   declares `EngineAllowListParserInterface` (`parse`), docstring only.
3. `worker` in `src/vibey/cli/main.py:1471-1477` becomes:
   ```python
    try:
        parsed = ENGINE_ALLOW_LIST_PARSER.parse(engines_opt)
    except ValueError as exc:
        typer.echo(f"Invalid engine: {exc}")
        raise typer.Exit(2) from exc
    allow_list = parsed.engines
    for token, engine in parsed.resolved:
        typer.echo(f"{token} resolves to {engine} (8.b: VS Code is the default IDE for paid loops)")
   ```
   Nothing else in `worker` changes. Use edit_file; `main.py` is 1700+ lines.
4. `EngineAuthCheck`'s classmethod at `cluster_preflight.py:153-171` replaces its two-line
   parse (`:168-170`) with `allow_list = ENGINE_ALLOW_LIST_PARSER.parse(engines).engines`; its
   docstring's "Raises ValueError naming the offending value" stays true.

## Where to change
- New `src/vibey/domain/engine_allow_list.py`, `src/vibey/domain/interfaces/engine_allow_list_interface.py`.
- `src/vibey/cli/main.py` and `src/vibey/infrastructure/cluster_preflight.py` (edit_file).
- New `tests/domain/test_engine_allow_list.py`; append two tests to
  `tests/cli/test_operational_commands.py` (never rewrite it).

## Acceptance criteria
- [ ] `grep -n "EngineId(e.strip())" src/vibey/cli/main.py src/vibey/infrastructure/cluster_preflight.py` prints nothing.
- [ ] `test_worker_invalid_engine` (`tests/cli/test_operational_commands.py:1419-1422`) and
      every cluster-preflight test pass unchanged.
- [ ] 100% branch coverage of `src/vibey/domain/*`, `src/vibey/infrastructure/*` and `src/vibey/cli/*`.

## Tests to write first (TDD)
`tests/domain/test_engine_allow_list.py`:
- `test_no_value_means_no_allow_list` -- `None`, `""` and `" , "` give `EngineAllowList(None, ())`.
- `test_named_engines_parse_to_ids` -- `"claudeloop, agyloop"`.
- `test_paid_ide_resolves_and_is_recorded` -- `"claudeloop,paid-ide"` gives `{EngineId.CLAUDELOOP, <the catalogue ide as EngineId>}` and one resolution.
- `test_an_unknown_engine_raises_valueerror` -- `"nonexistent"`, with `EngineId`'s own message.
- `test_parser_satisfies_its_interface`.
Append to `tests/cli/test_operational_commands.py`:
- `test_worker_announces_the_paid_ide_resolution` -- `runner.invoke(app, ["worker", "--engines", "paid-ide", "--azure", "bogus"])` exits 2 on the `--azure` check (`main.py:1481-1483`, reached before any database) and its output contains `paid-ide resolves to vscode-paid (8.b: VS Code is the default IDE for paid loops)`. Mark it `@pytest.mark.usefixtures("_fast_engine_preflight")` like its neighbours.
- `test_worker_names_nothing_when_no_ide_is_unnamed` -- the same with `--engines claudeloop`: no `resolves to` line.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain tests/infrastructure/test_cluster_preflight.py tests/cli/test_operational_commands.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- `vibey.toml` parsing (`gap-paid-ide-default-1`); the `paidloop` token and `[engines.vscode_paid]`
  (ADR-0046 lanes, `loops-vscode-paid`); the chart's `worker.engines` (it passes the same
  string through, so it gains the token for free).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(cli): --engines paid-ide resolves to vscode-paid, and the worker says so`. Do not push.

## Lane card
- **Depends on:** `gap-paid-ide-default-1`, `loops-vscode-paid`.
- **Must keep passing unchanged:** `tests/cli/test_operational_commands.py`'s existing tests,
  `tests/infrastructure/test_cluster_preflight.py`, every protected test.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
