<!-- split of #331: child 3 of 5; audit: issue-audit/updates/331.md -->

## Title
feat(azure): the az adapter declares its provider and preflight

## Why
`vibey worker --azure az` checks that `az` is logged in with a raw
`subprocess.run(["az", "account", "show", "-o", "none"], ...)` inside the CLI
(`src/vibey/cli/main.py:1488-1490`), before the project is even resolved, and its tests can only
reach it by patching `vibey.cli.main.subprocess.run` (`tests/cli/test_operational_commands.py:1991-2025`).
Sub-doctrine 9.b (`src/vibey_tools/gh/docs/doctrines.md:349`) says substitution happens at the
declared seam, never by patching an import. `AzCliClientAdapter`
(`src/vibey/infrastructure/azure/az_cli.py:47-165`) already runs every command through an injected
`CommandExecutor` (`az_cli.py:48-55`), so the preflight belongs there, declared as data beside the
provider it serves (12.c, `doctrines.md:455`). This lane gives the az adapter the same
`PROVIDER`/`PREFLIGHT_ARGV`/`LOGIN_HINT` class attributes and `preflight()` method that the OpenStack
adapter (lane `split-331-2-openstack-cli-adapter`) declares, so lane
`split-331-4-worker-cloud-flag` can select either adapter the same way and delete the raw
`subprocess.run`.

## Required behaviour
1. `AzCliClientAdapter` gains three class attributes (`typing.ClassVar`), exactly:
   ```python
   PROVIDER: ClassVar[str] = "azure"
   PREFLIGHT_ARGV: ClassVar[tuple[str, ...]] = ("az", "account", "show", "-o", "none")
   LOGIN_HINT: ClassVar[str] = "a logged-in Azure CLI: run `az login` first"
   ```
2. `_require_provider(scope)` (added by lane `split-330-4-az-scope-guard`) compares against
   `self.PROVIDER` instead of the literal `"azure"`, and its message becomes
   `f"the az adapter deploys provider {self.PROVIDER!r} only; this scope is {scope.provider!r}"`,
   which is byte-identical to the message it has today
   (`"the az adapter deploys provider 'azure' only; this scope is ..."`), so the tests that lane
   added keep passing unedited.
3. A new method, through the injected executor:
   ```python
   async def preflight(self) -> bool:
       """Whether `az` is installed and logged in.

       Runs PREFLIGHT_ARGV through the injected executor; `vibey worker --cloud cli`
       asks this before trusting a worker to real infrastructure. A missing `az`
       binary reaches here as an OSError from the executor and means not ready.
       """
       try:
           result = await self._executor.execute(self.PREFLIGHT_ARGV)
       except OSError:
           return False
       return result.returncode == 0
   ```
   It must not go through `_az_json` (which appends `-o json` and raises on failure).
4. The module docstring (`az_cli.py:2-16`) names the new switch. In the sentence at lines 4-5,
   replace ``(`vibey worker --azure az`)`` with
   ``(`vibey worker --cloud cli` with `[deploy].target = "azure"`)``. Replace the last sentence
   (lines 13-15, from "`az` must be installed and logged in" to the closing period) with:
   ``"`az` must be installed and logged in (`az login`); `preflight()` runs `az account show -o none` through the injected executor before a worker is trusted to this adapter."``
5. Nothing else in the adapter changes: its commands, errors and consent checks stay as they are.

## Where to change
Line numbers are from the storm integration branch at `4317cff6`, before lane
`split-330-4-az-scope-guard` added `_require_provider` and its import; find the quoted text if a
line has moved. Use `edit_file` for both files.
- `src/vibey/infrastructure/azure/az_cli.py`:
  - line 22: `from typing import Any` becomes `from typing import Any, ClassVar`;
  - inside `class AzCliClientAdapter:` (line 47), before `def __init__`, add the three class
    attributes of Required behaviour 1;
  - in `_require_provider`, replace `if scope.provider != "azure":` with
    `if scope.provider != self.PROVIDER:` and make the message the f-string of Required behaviour 2;
  - add `preflight` (Required behaviour 3) directly after `__init__`;
  - the docstring edits of Required behaviour 4.
- `tests/infrastructure/azure/test_az_cli.py`: append the helper class and the two tests below
  (EDITING-RULES.md rule 3: append; never rewrite the file). The existing `FakeExecutor`
  (`test_az_cli.py:84-95`) keys answers by `argv[1:3]` and cannot raise, so the appended tests use
  their own one-answer double at the same constructor seam. If `tests/fakes/process.py` defines
  `ScriptedCommandExecutor` when you start, you may script `("az", "account", "show", "-o", "none")`
  with it instead; the assertions do not change.

Only these two files change.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/infrastructure/azure` passes, including every test
      lane `split-330-4-az-scope-guard` added, unedited.
- [ ] `uv run pytest -q -p no:cacheprovider --noconftest -n 0 tests/infrastructure/azure/test_az_cli.py`
      passes with PostgreSQL stopped.
- [ ] `grep -n '"azure"' src/vibey/infrastructure/azure/az_cli.py` shows only the `PROVIDER` line
      (and the docstring's `[deploy].target = "azure"`).
- [ ] `grep -nE "monkeypatch|mock|patch\(" tests/infrastructure/azure/test_az_cli.py` prints nothing.
- [ ] `git diff --stat` names only `az_cli.py` and `test_az_cli.py`.
- [ ] `uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100` passes after
      the whole-suite coverage run.

## Tests to write first (TDD)
Append to `tests/infrastructure/azure/test_az_cli.py` (it already imports `pytest`,
`AzCliClientAdapter` and `CommandResult`):
```python
class _OneAnswer:
    """A CommandExecutor that answers every argv with one scripted result, or raises it."""

    def __init__(self, answer: CommandResult | BaseException) -> None:
        self.answer = answer
        self.calls: list[tuple[str, ...]] = []

    async def execute(self, argv: tuple[str, ...]) -> CommandResult:
        self.calls.append(argv)
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer
```
- `test_az_preflight_is_declared_on_the_adapter`: `AzCliClientAdapter.PROVIDER == "azure"`,
  `AzCliClientAdapter.PREFLIGHT_ARGV == ("az", "account", "show", "-o", "none")`, and
  ``AzCliClientAdapter.LOGIN_HINT == "a logged-in Azure CLI: run `az login` first"``.
- `test_az_preflight_is_ready_only_when_the_account_shows`, parametrized over `(answer, ready)`:
  `(CommandResult(0, "", ""), True)`,
  `(CommandResult(1, "", "Please run 'az login' to setup account."), False)` and
  `(FileNotFoundError(2, "No such file or directory", "az"), False)`. With
  `executor = _OneAnswer(answer)`, `await AzCliClientAdapter(executor=executor).preflight() is ready`
  and `executor.calls == [("az", "account", "show", "-o", "none")]`.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run pytest -q -p no:cacheprovider tests/infrastructure/azure
uv run pytest -q -p no:cacheprovider --noconftest -n 0 tests/infrastructure/azure/test_az_cli.py
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
```
One coverage run at a time. Until lane `fakes-harness-decouple` lands, `tests/conftest.py:146-156`
connects to PostgreSQL at session start, so every run except the `--noconftest` one needs
PostgreSQL 17 reachable. If `ruff check` reports only import order (`I001`), run
`uv run ruff check --select I --fix` on the files you changed, then `uv run ruff format` on them.

## Out of scope
- `src/vibey/cli/main.py` and its tests: lane `split-331-4-worker-cloud-flag` replaces the raw
  `subprocess.run` with this `preflight()`. The CLI still calls `subprocess.run` after this lane.
- The OpenStack adapter (lane `split-331-2-openstack-cli-adapter`) and the Heat renderer.
- An interface file for `AzCliClientAdapter` (it has none today; adding
  `infrastructure/azure/interfaces/` is its own change), the ARM renderer, `az_cli.py`'s own
  `MutationNotAuthorized`, and the in-memory adapter.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md, README.md or the skill
  trees. Do not push, open PRs, or change git remotes. Commit locally as
  `feat(azure): the az adapter declares its provider and preflight`; the hooks add the
  `Made-With:` trailer.

## Standing constraints
- Tests substitute only at the constructor's `executor=` seam: never `monkeypatch.setattr`,
  `mock.patch`, `MagicMock` or `AsyncMock` (9.b).
- Never shell out with `shell=True`; `PREFLIGHT_ARGV` is a fixed tuple.
- Change existing files with `edit_file` or a checked replacement; never rewrite an existing file
  (EDITING-RULES.md). Keep line 1 (the provenance header) of both files.
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.

**Depends on:** split-330-4-az-scope-guard
- split-330-4-az-scope-guard: `_require_provider` in `az_cli.py` (and `ScopeProviderMismatchError`),
  which this lane makes compare against `self.PROVIDER`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
