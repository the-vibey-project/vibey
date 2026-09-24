## Title
feat(ledger): vibey ledger search --all-projects searches everything a deployment holds, human output first

## Why
Sub-doctrine 7.a (`src/vibey_tools/gh/docs/doctrines.md:72-78`): anyone can search "the full
public ledger where a deployment holds it", and the explorer is "optimized for human consumption
first and machine consumption after". `vibey ledger search` is "an operator's search over one
project's ledger" (`src/vibey/cli/ledger_search.py:4-5`) and resolves exactly one project
(`:207-218`). `gap-ledger-search-all-projects-1` gave the port `LedgerSearch.search_all(query)`.
This lane exposes it as `--all-projects`, with the same human-first lines, each naming its
project, and the same `--json` document shape.

## Required behaviour
1. `ledger_search(...)` (`:226-287`) gains, after `as_json`,
   `all_projects: Annotated[bool, typer.Option("--all-projects", help="Search every project this deployment holds (7.a). Do not also name a project.")] = False`,
   and passes `all_projects=all_projects` to `LEDGER_SEARCH.run(...)`. Its docstring gains
   ", in one project or, with --all-projects, every project".
2. `LedgerSearchCommand.run(self, project_id, query, *, as_json, all_projects: bool = False)`:
   - First, before any note and before the app is opened: if `all_projects and project_id is not None`,
     `raise typer.BadParameter("--all-projects searches every project; do not also name one")`
     (a usage error, exit 2, as the other checks are, `:186-188`).
   - Without `all_projects`: exactly today's path.
   - With it: `result = await resources.ledger_search.search_all(query)` inside the same
     `async with self._open_app() as resources:`; then `names = await self._names(resources, result)`.
     JSON prints `self._presenter.machine(None, result)`; otherwise
     `"\n".join(self._presenter.human(result, projects=names))`.
3. `@staticmethod async def _names(resources: AppResources, result: LedgerSearchResultInterface) -> dict[UUID, str]`:
   for each distinct `event.project_id` in `result.events`, the project's `name` from
   `await resources.projects.get(project_id)`, or `str(project_id)[:8]` when it returns `None`.
4. `LedgerSearchPresenter`:
   - `human(self, result, *, projects: Mapping[UUID, str] | None = None) -> list[str]`. With
     `projects`, every event line is `f"{projects[event.project_id]} " + <today's line>`, and the
     final count line is `f"{count} matching event{'' if count == 1 else 's'} across {n} project{'' if n == 1 else 's'}"`
     where `n` is the number of distinct projects in the result. The "no events match" line and the
     truncation line are unchanged. Without `projects`, today's output exactly.
   - `machine(self, project_id: UUID | None, result) -> str`. For `None`, the document is
     `{"scope": "all-projects", "truncated": ..., "events": [...]}` (every event record already
     carries its `project_id`, `:123-138`). For a project id, today's document exactly.
5. `src/vibey/cli/interfaces/ledger_search_interface.py`: `human`, `machine` and
   `LedgerSearchCommandInterface.run` declare the new signatures, with one-line docstrings.
6. The module docstring's first paragraph (`:4-8`) says the search covers one project, or every
   project a deployment holds with `--all-projects`.

## Where to change
- `src/vibey/cli/ledger_search.py`, `src/vibey/cli/interfaces/ledger_search_interface.py` (edit_file only).
- Append to `tests/cli/test_ledger_search_cli.py` (in-memory since `fakes-cli-ledger-deploy`:
  seed through `async with memory_app.open_app() as resources:` and `resources.ledger.append(...)`,
  create projects through `resources.projects`, invoke with
  `ops.invoke(memory_app, "ledger", "search", ...)`, `tests/cli/ops_support.py`).

## Acceptance criteria
- [ ] With projects `alpha` and `beta` each holding events, `vibey ledger search --all-projects`
      prints one line per event, oldest first, each starting with its project's name, then
      `N matching events across 2 projects`; exit 0.
- [ ] `--all-projects --json` prints one JSON document with `"scope": "all-projects"`, no
      `project_id` key, and every event's `project_id`.
- [ ] `vibey ledger search <id> --all-projects` exits 2 with the usage message, and the app is
      never opened.
- [ ] `--all-projects --limit 2` over three matches prints the truncation line.
- [ ] An event whose project has no row is labelled by the first eight characters of its id.
- [ ] Every existing test in `tests/cli/test_ledger_search_cli.py` passes unchanged: one-project
      output is byte-for-byte today's.
- [ ] 100% branch coverage of `src/vibey/cli/*`.

## Tests to write first (TDD)
Append to `tests/cli/test_ledger_search_cli.py`:
- `test_all_projects_names_each_events_project_oldest_first`
- `test_all_projects_json_is_one_document_scoped_to_the_deployment`
- `test_all_projects_with_a_named_project_is_a_usage_error` (an `open_app` that raises
  `AssertionError("opened")` when entered, passed through `LedgerSearchCommand(open_app=...)`;
  `pytest.raises(typer.BadParameter)` on `run`)
- `test_all_projects_says_when_older_matches_were_left_out`
- `test_all_projects_with_no_events_says_so`
- `test_an_event_whose_project_is_gone_is_labelled_by_its_id` (append an event for a random
  project id to the in-memory ledger)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider -m "not integration and not paid" tests/cli tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- The store and the port (`gap-ledger-search-all-projects-1`).
- `vibey ledger show` and the published site.
- `docs/reference/cli.md` (the docs wave documents the option).
- Docs, CHANGELOG.

Commit as `feat(ledger): vibey ledger search --all-projects searches everything a deployment holds`. Do not push.

## Lane card
- **Depends on:** `gap-ledger-search-all-projects-1`, `fakes-cli-ledger-deploy`, `orm-app-resources`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
