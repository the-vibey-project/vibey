# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A tenant cannot drift back to loose typing, nor be strict in config and unchecked in CI (SP4-B).

Two claims, both read from the declarations rather than from a run:

* every tenant `pyproject.toml` that has a `[tool.mypy]` table says `strict = true`, and
  loosens nothing beyond the explicit, reasoned allow-list below;
* every such tenant has a `static` command naming mypy on the 3.12 cell of the generated
  `tools` matrix (read from `.github/ci-matrices.toml`, the source the matrix is generated
  from), or a `tools-lint` step run from its directory, so strict-in-config is also
  checked-in-CI.
"""

import re
import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml

from .ci_matrix_rows import CiMatrixRows

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"
TENANT_ROOTS = ("src/vibey_runners", "src/vibey_tools")

# Options that make mypy looser than `strict = true` plus the options strict already implies.
# Each entry is (tenant dir, option, the value it may hold, the written reason). Anything not
# listed here fails. There is no exception to `strict = true` itself.
LOOSENING_OPTIONS = {
    "warn_unused_ignores",
    "disallow_untyped_defs",
    "disallow_incomplete_defs",
    "disallow_untyped_calls",
    "disallow_any_generics",
    "check_untyped_defs",
    "no_implicit_optional",
    "warn_return_any",
    "warn_redundant_casts",
    "warn_no_return",
    "ignore_errors",
    "disable_error_code",
    "allow_untyped_defs",
}
ALLOWED_LOOSENINGS: list[tuple[str, str, Any, str]] = [
    (
        "src/vibey_tools/bootstrap",
        "warn_unused_ignores",
        False,
        "Cloud SDK stubs (azure.*, opentelemetry.*) are optional extras, so whether a "
        "`type: ignore` is needed depends on which extras are installed; with strict's "
        "warn_unused_ignores the same line would be an error in one CI cell and not another.",
    ),
]


def _relative(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def _tenants_with_mypy() -> list[Path]:
    found = []
    for root in TENANT_ROOTS:
        for package in sorted((REPO / root).iterdir()):
            pyproject = package / "pyproject.toml"
            if pyproject.is_file() and "mypy" in _manifest(package).get("tool", {}):
                found.append(package)
    assert found, f"no tenant declares [tool.mypy] under {TENANT_ROOTS}; the roots moved"
    return found


def _manifest(package: Path) -> dict[str, Any]:
    with (package / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


@pytest.mark.parametrize("package", _tenants_with_mypy(), ids=_relative)
def test_the_tenant_mypy_table_is_strict(package: Path) -> None:
    table = _manifest(package)["tool"]["mypy"]
    assert table.get("strict") is True, (
        f"{_relative(package)}/pyproject.toml [tool.mypy] must say `strict = true`; "
        "there is no allow-list entry for strictness itself (SP4-B)."
    )


@pytest.mark.parametrize("package", _tenants_with_mypy(), ids=_relative)
def test_the_tenant_loosens_nothing_without_a_written_reason(package: Path) -> None:
    where = _relative(package)
    table = _manifest(package)["tool"]["mypy"]
    allowed = {(w, opt): value for w, opt, value, reason in ALLOWED_LOOSENINGS if w == where}
    loosened = [
        option
        for option in sorted(LOOSENING_OPTIONS & set(table))
        # `strict` already switches these on, so setting them True restates strictness.
        if table[option] is not True or option in {"ignore_errors", "allow_untyped_defs"}
        if allowed.get((where, option), object()) != table[option]
    ]
    assert not loosened, (
        f"{where} loosens {loosened} below `strict = true` with no entry in "
        "ALLOWED_LOOSENINGS (tests/meta/test_tenant_mypy_is_strict.py). Add a written reason "
        "or remove the option."
    )


def test_every_allow_listed_loosening_still_exists_and_has_a_reason() -> None:
    for where, option, value, reason in ALLOWED_LOOSENINGS:
        table = _manifest(REPO / where)["tool"]["mypy"]
        assert table.get(option) == value, f"{where}: stale allow-list entry for {option}"
        assert len(reason.split()) >= 8, f"{where}: {option} needs a real written reason"


def _mypy_commands_run_from(where: str) -> list[str]:
    """The mypy commands CI runs from `where` on the 3.12 floor cell, or in `tools-lint`."""
    commands = [
        str(row["static"])
        for row in CiMatrixRows.full("tools")
        if str(row["dir"]) == where and str(row["python"]) == "3.12" and row.get("static")
    ]
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    commands += [
        str(step["run"])
        for step in workflow["jobs"]["tools-lint"]["steps"]
        if step.get("working-directory") == where and step.get("run")
    ]
    return [command for command in commands if re.search(r"(?<![\w-])mypy(?![\w-])", command)]


@pytest.mark.parametrize("package", _tenants_with_mypy(), ids=_relative)
def test_a_strict_tenant_is_checked_in_ci(package: Path) -> None:
    where = _relative(package)
    assert _mypy_commands_run_from(where), (
        f"{where} is configured `strict = true` but no `static` command naming mypy runs on "
        "its 3.12 `tools` matrix row (.github/ci-matrices.toml) and no `tools-lint` step runs "
        "it. Strict in config and unchecked in CI is a claim, not a gate."
    )
