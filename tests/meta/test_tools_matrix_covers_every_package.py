# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The `tools` matrix in ci.yml covers every absorbed package that has a suite.

ADR-0022: an absorbed package keeps every gate it arrived with, and "a floor nothing
runs on is a claim, not a contract". That principle applies to matrix MEMBERSHIP just
as much as to the floors inside a row. The matrix was added with three packages and
five more were absorbed (ADR-0021) without anyone noticing the rows were missing --
for months nothing in this repository ran the five session runners' suites. Nothing
would have caught it: no test in this tree read .github/workflows at all.

So this is the guard. It needs no Postgres and no network, and it fails against the
tree as it stood before the runner rows landed.

Two rules, both derived rather than enumerated, because a hard-coded package list is
the same defect one layer up (ADR-0018 -- a value that could be a key is a decision
taken away from the next adopter):

1. Membership. Every directory under src/vibey_runners/ and src/vibey_tools/ that has
   a pyproject.toml AND a suite directory needs a row. The suite directory is what
   makes it gateable -- src/vibey_runners/common is excluded by that rule and not by
   name, because it genuinely ships no tests. If it grows some, this test starts
   demanding a row for it, which is the correct answer.

2. The floor actually runs. A package's requires-python floor is the oldest
   interpreter it promises to work on. If no row runs that interpreter, the promise
   is untested -- exactly ADR-0022's "a floor nothing runs on is a claim". claudeloop
   publishes 3.10 and is the only member of this tree that does; this is the assertion
   that keeps its 3.10 row from being quietly dropped to match everything else.

3. The static gates actually run (#263). The rows above ran every runner's suite and
   none of its mypy, lint-imports or bandit. Those lived only in each tenant's nested
   workflow, which GitHub never reads, and CONTRIBUTING.md said they ran anyway. So
   the gates are derived from the tenant's own pyproject, not listed here: a
   `[tool.mypy]` table means mypy, `[tool.importlinter]` means lint-imports, and
   bandit named in an extra means bandit. Each must appear in a command root CI runs
   from that tenant's directory, which is a row's `static` or a `tools-lint` step.
   A tenant that configures a gate nothing runs fails here, the way a missing row
   fails rule 1.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and tests/meta/test_adr_counts.py established the
shape for this directory. The rule is about production code; a collected test function
is the framework's own interface.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"
TENANT_ROOTS = ("src/vibey_runners", "src/vibey_tools")
SUITE_DIRS = ("tests", "test")
FLOOR = re.compile(r">=\s*(\d+\.\d+)")


def _matrix_rows() -> list[dict[str, Any]]:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    rows = workflow["jobs"]["tools"]["strategy"]["matrix"]["include"]
    assert rows, "the tools job has no matrix rows"
    return list(rows)


def _gateable_packages() -> list[Path]:
    """Every tenant that ships both a pyproject.toml and a suite to run."""
    found = [
        package
        for root in TENANT_ROOTS
        for package in sorted((REPO / root).iterdir())
        if (package / "pyproject.toml").is_file()
        and any((package / suite).is_dir() for suite in SUITE_DIRS)
    ]
    assert found, f"no gateable tenants found under {TENANT_ROOTS}; the roots moved"
    return found


def _relative(package: Path) -> str:
    return package.relative_to(REPO).as_posix()


def _requires_python_floor(package: Path) -> str:
    with (package / "pyproject.toml").open("rb") as handle:
        requires = tomllib.load(handle)["project"]["requires-python"]
    match = FLOOR.search(requires)
    assert match, f"{_relative(package)} declares requires-python {requires!r} with no >= floor"
    return match.group(1)


def test_every_gateable_package_has_a_tools_row() -> None:
    # A row counts only if it runs a suite: the suite step is conditional on `test`, so
    # that a static-only row can exist, and a suite-less row must not satisfy this.
    covered = {str(row["dir"]) for row in _matrix_rows() if row.get("test")}
    missing = [_relative(p) for p in _gateable_packages() if _relative(p) not in covered]
    assert not missing, (
        f"absorbed packages with a suite and no `tools` matrix row: {missing}. "
        "ADR-0022: an absorbed package keeps every gate it arrived with."
    )


@pytest.mark.parametrize("package", _gateable_packages(), ids=_relative)
def test_every_package_floor_is_actually_run(package: Path) -> None:
    floor = _requires_python_floor(package)
    where = _relative(package)
    interpreters = {str(row["python"]) for row in _matrix_rows() if str(row["dir"]) == where}
    assert floor in interpreters, (
        f"{where} publishes a {floor} floor but the `tools` matrix runs it only on "
        f"{sorted(interpreters)}. ADR-0022: a floor nothing runs on is a claim, not a contract."
    )


def _tenants() -> list[Path]:
    """Every tenant with a pyproject, suite or not: a static gate needs no suite."""
    found = [
        package
        for root in TENANT_ROOTS
        for package in sorted((REPO / root).iterdir())
        if (package / "pyproject.toml").is_file()
    ]
    assert found, f"no tenants found under {TENANT_ROOTS}; the roots moved"
    return found


def _configured_static_gates(package: Path) -> list[str]:
    """The static gates a tenant's own pyproject says it is held to."""
    with (package / "pyproject.toml").open("rb") as handle:
        manifest = tomllib.load(handle)
    tool = manifest.get("tool", {})
    extras = manifest.get("project", {}).get("optional-dependencies", {})
    declared = {
        re.split(r"[\s\[<>=!~;]", requirement, maxsplit=1)[0].lower()
        for requirements in extras.values()
        for requirement in requirements
    }
    gates = []
    if "mypy" in tool:
        gates.append("mypy")
    if "importlinter" in tool:
        gates.append("lint-imports")
    if "bandit" in declared:
        gates.append("bandit")
    return gates


def _commands_run_from(where: str) -> list[str]:
    """Every static command root CI runs with `where` as its working directory."""
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    commands = [
        str(row["static"])
        for row in workflow["jobs"]["tools"]["strategy"]["matrix"]["include"]
        if str(row["dir"]) == where and row.get("static")
    ]
    commands += [
        str(step["run"])
        for step in workflow["jobs"]["tools-lint"]["steps"]
        if step.get("working-directory") == where and step.get("run")
    ]
    return commands


@pytest.mark.parametrize("package", _tenants(), ids=_relative)
def test_every_configured_static_gate_is_run(package: Path) -> None:
    where = _relative(package)
    commands = _commands_run_from(where)
    unrun = [
        gate
        for gate in _configured_static_gates(package)
        if not any(re.search(rf"(?<![\w-]){re.escape(gate)}(?![\w-])", c) for c in commands)
    ]
    assert not unrun, (
        f"{where} configures {unrun} but no `static` row and no `tools-lint` step runs it "
        "from that directory. ADR-0022: a gate a tenant arrived with is kept, not declared."
    )


@pytest.mark.parametrize("package", _tenants(), ids=_relative)
def test_static_gates_run_on_the_floor(package: Path) -> None:
    where = _relative(package)
    static_rows = [row for row in _matrix_rows() if str(row["dir"]) == where and row.get("static")]
    if not static_rows:
        pytest.skip(f"{where} has no `static` row")
    floor = _requires_python_floor(package)
    interpreters = sorted({str(row["python"]) for row in static_rows})
    assert floor in interpreters, (
        f"{where} runs its static gates only on {interpreters}, not on its {floor} floor. "
        "The floor is where its declared dependencies resolve at their oldest."
    )
