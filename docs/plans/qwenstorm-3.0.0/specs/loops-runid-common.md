## Title
feat(runners-common): RunId, the run-id validator every runner copies, moves into vibey_runners.common

ADR-0046 lane L19 (slug `loops-runid-common`).

## Why
Draft ADR-0046 §10 (`specs/ADR-two-loops.md:307`) puts "`RunId`, the run-id validator every
runner copies today" in `vibey_runners.common`, and non-negotiable 5 (`:338`) says "The run-id
validator moves into `vibey_runners.common`, not into a sixth copy". Sub-doctrine 10.e
(`src/vibey_tools/gh/docs/doctrines.md:417`) forbids a second implementation of what the family
ships; 9.b (`:349`) wants the class's interface beside it.

At integration `d3b4a388` the validator lives in `src/vibey_runners/opencode/src/opencodeloop/domain/model.py:10-32`
(pattern `\A[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z`), mirrored by
`src/vibey_runners/opencode/src/opencodeloop/domain/interfaces/model_interface.py:15-20`; the
other runners keep their own copies (`src/vibey_runners/{claude,codex,cursor,agy}/src/*/infrastructure/rundir.py`).
`vibey_runners.common` (`src/vibey_runners/common/src/vibey_runners/common/`) has only an
`application/` package and ships no tests: its CI rows run only static gates
(`.github/workflows/ci.yml:317-335`, comment "vibey-runners-common ships no suite"). Lane
`loops-vscodeloop-scaffold` is the first consumer; moving the existing runners onto it is not this
lane.

## Required behaviour
1. `vibey_runners.common.domain.run_id.RunId` is `opencodeloop.domain.model.RunId` exactly:
   a `@dataclass(frozen=True, slots=True)` with `value: str` and
   `@classmethod parse(cls, raw: str) -> "RunId"`, which strips `raw`, matches
   `\A[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z`, and otherwise raises
   `ValueError(f"invalid run id {raw!r}: must be 1-128 characters of letters, digits, '.', '_' or '-', and start with a letter or digit")`
   — the message byte for byte as `model.py:28-31` builds it (two adjacent string literals).
2. `vibey_runners.common.domain` exports `RunId`; `vibey_runners.common.domain.interfaces`
   exports `RunIdInterface`, a `@runtime_checkable` Protocol with a read-only `value: str`
   property (copied from `model_interface.py:15-20`).
3. The domain package is pure: it imports only the standard library and itself. The package
   keeps `dependencies = []` (`src/vibey_runners/common/pyproject.toml:14`).
4. The tenant ships a suite: `src/vibey_runners/common/tests/test_run_id.py`. Its pytest settings
   already exist (`pyproject.toml:49-51`, `testpaths = ["tests"]`).
5. CI runs it: each of the three `vibey-runners-common` rows (`ci.yml:321-335`) gains
   `test: 'python -m pytest -q'`, so `tests/meta/test_tools_matrix_covers_every_package.py`
   (whose rule 1 demands a row with `test` for every tenant with a suite directory, `:106-114`, and whose `test_every_package_compatibility_range_is_actually_run` wants every supported interpreter, `:117-128`)
   finds 3.12, 3.13 and 3.14. The comment above the rows (`:317-320`) is corrected.
6. `opencodeloop` is not edited (lane `loops-remove-opencode-tenant` deletes it later).

## Where to change
Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` first. Line 1 of every new
file is the provenance comment copied byte for byte from line 1 of
`src/vibey_runners/common/src/vibey_runners/common/__init__.py`. The package directory is
`src/vibey_runners/common/src/vibey_runners/common/` (call it PKG below); the tenant directory is
`src/vibey_runners/common/`.
- New `PKG/domain/__init__.py`, i.e. `src/vibey_runners/common/src/vibey_runners/common/domain/__init__.py`:
  ```python
  """Pure values shared by the session runners (ADR-0046 §10): no I/O, standard library only."""

  from vibey_runners.common.domain.run_id import RunId

  __all__ = ["RunId"]
  ```
- New `PKG/domain/run_id.py`:
  ```python
  """The run id every runner validates: exactly one safe path segment (ADR-0046 §10).

  A run id becomes one directory name under a runner's `runs/`. The pattern admits letters,
  digits, dot, underscore and hyphen, and refuses a leading dot, so `../..` or `.hidden` can
  never be built from caller input. Moved here from opencodeloop (10.e) so no runner keeps a
  copy of its own.
  """

  import re
  from dataclasses import dataclass

  _RUN_ID_PATTERN = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


  @dataclass(frozen=True, slots=True)
  class RunId:
      """A validated run identifier that is safe as a single path segment.

      Declared by ``interfaces/run_id_interface.py::RunIdInterface``.
      """

      value: str

      @classmethod
      def parse(cls, raw: str) -> "RunId":
          """Return a validated run id, or raise ValueError naming what is wrong."""
          candidate = raw.strip()
          if not _RUN_ID_PATTERN.match(candidate):
              raise ValueError(
                  f"invalid run id {raw!r}: must be 1-128 characters of letters, "
                  "digits, '.', '_' or '-', and start with a letter or digit"
              )
          return cls(candidate)


  __all__ = ["RunId"]
  ```
- New `PKG/domain/interfaces/__init__.py`:
  ```python
  """Interfaces for the shared runner domain values (ADR-0016)."""

  from vibey_runners.common.domain.interfaces.run_id_interface import RunIdInterface

  __all__ = ["RunIdInterface"]
  ```
- New `PKG/domain/interfaces/run_id_interface.py`:
  ```python
  """The declared seam for the shared run id (ADR-0016, sub-doctrine 9.b)."""

  from typing import Protocol, runtime_checkable


  @runtime_checkable
  class RunIdInterface(Protocol):
      """A validated run identifier that is safe as a single path segment."""

      @property
      def value(self) -> str: ...
  ```
- New `src/vibey_runners/common/tests/test_run_id.py` (in the tenant directory, not PKG; no `__init__.py`: the tenant suites
  under `src/vibey_runners/*/tests` have none).
- `.github/workflows/ci.yml` (over 100 lines): the three rows and the comment. Save this program
  to a scratch file outside the repository (for example `/tmp/l19_ci.py`) and run
  `python3 /tmp/l19_ci.py` from the repository root (Python, not `sed -i`: GNU and BSD sed differ, 8.h):
  ```python
  from pathlib import Path

  p = Path(".github/workflows/ci.yml")
  s = p.read_text()
  row = "            static: 'mypy --strict src/vibey_runners/common && lint-imports'\n"
  assert s.count(row) == 3, s.count(row)
  s = s.replace(row, row + "            test: 'python -m pytest -q'\n")
  old = (
      "          # vibey-runners-common ships no suite, so it has no `test` and the suite step\n"
      "          # skips it (tests/meta/test_tools_matrix_covers_every_package.py counts only rows\n"
      "          # that do carry one). Its row exists for `static`: it declares a strict mypy and\n"
      "          # two import contracts, and until this row nothing had ever run either.\n"
  )
  new = (
      "          # vibey-runners-common's suite covers its shared domain values (ADR-0046: `RunId`),\n"
      "          # and its rows run it beside `static`: a strict mypy and two import contracts,\n"
      "          # which nothing had ever run before these rows.\n"
  )
  assert s.count(old) == 1, s.count(old)
  p.write_text(s.replace(old, new))
  ```

## Acceptance criteria
- [ ] The tenant suite passes and covers `domain/` completely (the coverage command below).
- [ ] `tests/meta/test_tools_matrix_covers_every_package.py` passes.
- [ ] `git diff --stat HEAD -- src/vibey_runners/opencode` is empty.
- [ ] `grep -n "^dependencies = \[\]" src/vibey_runners/common/pyproject.toml` prints one line.
- [ ] The tenant's `mypy --strict` and `lint-imports` pass; root `ruff check` and `ruff format --check` pass.

## Tests to write first (TDD)
`src/vibey_runners/common/tests/test_run_id.py` (no service):
- `test_parse_accepts_a_plain_id_and_strips_whitespace`: `RunId.parse(" run-1.a_b ") == RunId("run-1.a_b")`.
- `test_parse_accepts_128_characters_and_refuses_129`: `"a" * 128` parses; `"a" * 129` raises `ValueError`.
- `test_parse_refuses_what_could_leave_the_runs_directory` (parametrized over `"../.."`,
  `".hidden"`, `"a/b"`, `""`, `"   "`, `"-lead"`): each raises `ValueError`.
- `test_the_message_names_the_raw_value`: `RunId.parse("../..")` raises with `str(exc) ==`
  `"invalid run id '../..': must be 1-128 characters of letters, digits, '.', '_' or '-', and start with a letter or digit"`.
- `test_run_id_is_a_frozen_value`: assigning `value` raises `dataclasses.FrozenInstanceError`;
  equal ids are equal and hash equal.
- `test_run_id_satisfies_its_interface`: `isinstance(RunId("x"), RunIdInterface)`, imported from
  `vibey_runners.common.domain.interfaces`, and `from vibey_runners.common.domain import RunId` works.
- `test_the_domain_imports_only_the_standard_library`: an `ast` walk of every `.py` file under
  the installed `vibey_runners/common/domain/` directory (find it from
  `Path(vibey_runners.common.domain.__file__).parent`) finds only imports whose top-level module
  is in `sys.stdlib_module_names` or is `vibey_runners`.

## Checks the lane must run (all must pass)
First run `uv run ruff format src/vibey_runners/common`.

    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run ruff check . && uv run ruff format --check .
    (cd src/vibey_runners/common && uv run python -m pytest -q -p no:cacheprovider)
    (cd src/vibey_runners/common && uv run python -m pytest -q -p no:cacheprovider --cov=vibey_runners.common.domain --cov-branch --cov-report=term-missing --cov-fail-under=100)
    (cd src/vibey_runners/common && uv run python -m mypy --strict src/vibey_runners/common && uv run lint-imports)
    uv run pytest -q -p no:cacheprovider tests/meta/test_tools_matrix_covers_every_package.py
    uv run lint-imports
    git diff --stat HEAD -- src/vibey_runners/opencode
    git diff --stat

## Out of scope
- Moving any existing runner onto the shared `RunId` (their own lanes; opencodeloop is removed
  by `loops-remove-opencode-tenant`); the vscodeloop tenant (lane `loops-vscodeloop-scaffold`).
- The tenant's `pyproject.toml` (its dependencies stay `[]`), its README and every other doc.
- Protected tests: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** none.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
