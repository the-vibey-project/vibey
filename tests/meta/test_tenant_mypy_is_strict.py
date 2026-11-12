# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A tenant cannot drift back to loose typing, nor be strict in config and unchecked in CI (SP4-B).

Two claims, both read from the declarations rather than from a run:

* every tenant `pyproject.toml` has a `[tool.mypy]` table saying `strict = true` (a tenant
  with none must pass `--strict` in its CI command), and neither that table nor any
  `[[tool.mypy.overrides]]` entry loosens anything beyond the explicit, reasoned allow-list;
* every tenant has a real mypy invocation over its own path on the 3.12 cell of BOTH tiers of
  the generated `tools` matrix (read from `.github/ci-matrices.toml`, the source the matrix is
  generated from), or in a `tools-lint` step run from its directory.
"""

import re
import shlex
import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml

from .ci_matrix_rows import CiMatrixRows

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"
TENANT_ROOTS = ("src/vibey_runners", "src/vibey_tools")

# Options that loosen mypy when they are explicitly False (strict switches each one on).
LOOSE_WHEN_FALSE = (
    "warn_unused_ignores",
    "disallow_untyped_defs",
    "disallow_incomplete_defs",
    "disallow_untyped_calls",
    "disallow_any_generics",
    "disallow_untyped_decorators",
    "disallow_subclassing_any",
    "check_untyped_defs",
    "no_implicit_optional",
    "warn_return_any",
    "warn_redundant_casts",
    "warn_no_return",
    "strict_equality",
    "extra_checks",
    "warn_unused_configs",
)
# Options that loosen mypy when they are True (or, for the list, non-empty).
LOOSE_WHEN_TRUE = (
    "ignore_errors",
    "ignore_missing_imports",
    "implicit_reexport",
    "allow_untyped_defs",
    "allow_untyped_calls",
    "allow_incomplete_defs",
    "allow_untyped_decorators",
    "allow_subclassing_any",
    "allow_any_generics",
)
# Each entry is (tenant dir, option, the value it may hold, the written reason). It applies to
# the tenant's top-level table and to its overrides. Anything not listed here fails. There is
# no exception to `strict = true` itself.
ALLOWED_LOOSENINGS: list[tuple[str, str, Any, str]] = [
    (
        "src/vibey_tools/bootstrap",
        "warn_unused_ignores",
        False,
        "Many lazy-import sites carry `# type: ignore[import-not-found]` to protect against "
        "optional extras (fastapi, apscheduler, and others) being absent in a downstream "
        "environment. In the dev environment those extras are installed, so mypy would flag "
        "the ignore as unused although it is needed downstream (pyproject.toml, v2.0.0).",
    ),
    (
        "src/vibey_tools/bootstrap",
        "ignore_missing_imports",
        True,
        "The Azure SDK, OpenTelemetry and other optional extras are not all installed in every "
        "environment, so their imports cannot be resolved; bootstrap sets this globally and "
        "again for azure.* and opentelemetry.* (pyproject.toml).",
    ),
]


def _relative(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def _manifest(package: Path) -> dict[str, Any]:
    with (package / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def _tenants() -> list[Path]:
    found = [
        package
        for root in TENANT_ROOTS
        for package in sorted((REPO / root).iterdir())
        if (package / "pyproject.toml").is_file()
    ]
    assert found, f"no tenants found under {TENANT_ROOTS}; the roots moved"
    return found


def _loosenings(where: str, table: dict[str, Any], label: str) -> list[str]:
    """Every way `table` (the top table or one override) is looser than strict, unallowed."""
    allowed = {(w, opt): value for w, opt, value, _ in ALLOWED_LOOSENINGS if w == where}

    def permitted(option: str) -> bool:
        return (where, option) in allowed and allowed[(where, option)] == table[option]

    found = [o for o in LOOSE_WHEN_FALSE if table.get(o) is False and not permitted(o)]
    found += [o for o in LOOSE_WHEN_TRUE if table.get(o) is True and not permitted(o)]
    if table.get("follow_imports") in {"skip", "silent"}:
        found.append("follow_imports")
    if table.get("disable_error_code"):
        found.append("disable_error_code")
    return [f"{label}:{option}" for option in found]


def _table_problems(where: str, mypy: dict[str, Any] | None) -> list[str]:
    """Why a tenant's `[tool.mypy]` table is not strict; empty when it is."""
    if mypy is None:
        return ["no [tool.mypy] table"]
    problems = [] if mypy.get("strict") is True else ["strict is not true"]
    problems += _loosenings(where, mypy, "mypy")
    for index, override in enumerate(mypy.get("overrides", [])):
        problems += _loosenings(where, override, f"overrides[{index}]")
    return problems


def _segments(command: str) -> list[list[str]]:
    return [shlex.split(part) for part in re.split(r"&&|\|\||;|\n", command) if part.strip()]


def _mypy_invocations(command: str) -> list[list[str]]:
    """The arguments of each real `mypy` / `python -m mypy` call in a shell command line."""
    calls = []
    for words in _segments(command):
        if words[:3] in (["python", "-m", "mypy"], ["python3", "-m", "mypy"]):
            calls.append(words[3:])
        elif words and words[0] == "mypy":
            calls.append(words[1:])
    return calls


def _checks_the_tenant(command: str, package: Path, strict_flag_required: bool) -> bool:
    """True if `command` runs mypy over a path of the tenant (or its configured packages)."""
    configured = "packages" in _manifest(package).get("tool", {}).get("mypy", {})
    for args in _mypy_invocations(command):
        paths = [a for a in args if not a.startswith("-")]
        if strict_flag_required and "--strict" not in args:
            continue
        if configured or any((package / path.rstrip("/")).exists() for path in paths):
            return True
    return False


def _tools_lint_commands(where: str) -> list[str]:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return [
        str(step["run"])
        for step in workflow["jobs"]["tools-lint"]["steps"]
        if step.get("working-directory") == where and step.get("run")
    ]


def _floor_static_commands(rows: list[dict[str, Any]], where: str) -> list[str]:
    return [
        str(row["static"])
        for row in rows
        if str(row["dir"]) == where and str(row["python"]) == "3.12" and row.get("static")
    ]


@pytest.mark.parametrize("package", _tenants(), ids=_relative)
def test_the_tenant_mypy_table_is_strict_and_loosens_nothing_unrecorded(package: Path) -> None:
    where = _relative(package)
    mypy = _manifest(package).get("tool", {}).get("mypy")
    if mypy is None:
        # No table: the only acceptable form is `--strict` on its CI command line.
        commands = _floor_static_commands(CiMatrixRows.full("tools"), where)
        assert any(_checks_the_tenant(c, package, True) for c in commands), (
            f"{where} has no [tool.mypy] table and no `mypy --strict` CI command: it is not held "
            "to strict typing (SP4-B)."
        )
        return
    assert not _table_problems(where, mypy), (
        f"{where}/pyproject.toml [tool.mypy] is looser than strict: "
        f"{_table_problems(where, mypy)}. Require `strict = true` (no allow-list for that) or "
        "record the looser option with a written reason in ALLOWED_LOOSENINGS."
    )


def test_every_allow_listed_loosening_still_exists_and_has_a_reason() -> None:
    for where, option, value, reason in ALLOWED_LOOSENINGS:
        table = _manifest(REPO / where)["tool"]["mypy"]
        assert table.get(option) == value, f"{where}: stale allow-list entry for {option}"
        assert len(reason.split()) >= 8, f"{where}: {option} needs a real written reason"


@pytest.mark.parametrize("package", _tenants(), ids=_relative)
@pytest.mark.parametrize("tier", ["full", "pr"])
def test_a_strict_tenant_is_checked_in_ci_on_every_tier(package: Path, tier: str) -> None:
    where = _relative(package)
    rows = CiMatrixRows.full("tools") if tier == "full" else CiMatrixRows.pr("tools")
    if not any(str(row["dir"]) == where for row in rows):
        pytest.skip(f"{where} has no row in the {tier} tier")
    commands = _floor_static_commands(rows, where)
    if tier == "full":
        commands += _tools_lint_commands(where)
    assert any(_checks_the_tenant(c, package, False) for c in commands), (
        f"{where} is configured strict but no `static` command in the {tier} tier's 3.12 row "
        "(.github/ci-matrices.toml) and no `tools-lint` step runs a real mypy over its path. "
        "Strict in config and unchecked in CI is a claim, not a gate."
    )


# ------------------------------------------------------------------ the guard guards itself
# Each mutation below must be caught by the rule it targets; none touches the tree.

BOOTSTRAP = "src/vibey_tools/bootstrap"
STRICT = {"strict": True}


@pytest.mark.parametrize(
    "mutation",
    [
        None,
        {"strict": False},
        {"strict": True, "disallow_untyped_decorators": False},
        {"strict": True, "disallow_subclassing_any": False},
        {"strict": True, "strict_equality": False},
        {"strict": True, "extra_checks": False},
        {"strict": True, "warn_unused_configs": False},
        {"strict": True, "implicit_reexport": True},
        {"strict": True, "follow_imports": "skip"},
        {"strict": True, "follow_imports": "silent"},
        {"strict": True, "ignore_missing_imports": True},
        {"strict": True, "overrides": [{"module": "x.*", "ignore_errors": True}]},
        {"strict": True, "overrides": [{"module": "x.*", "warn_unused_ignores": False}]},
    ],
)
def test_the_strictness_rule_catches_a_loosened_table(mutation: dict[str, Any] | None) -> None:
    assert _table_problems("src/vibey_tools/skills", mutation), f"missed: {mutation}"


def test_the_strictness_rule_accepts_strict_and_the_recorded_bootstrap_loosenings() -> None:
    assert not _table_problems("src/vibey_tools/skills", dict(STRICT))
    recorded = {
        "strict": True,
        "warn_unused_ignores": False,
        "ignore_missing_imports": True,
        "overrides": [{"module": "azure.*", "ignore_missing_imports": True}],
    }
    assert not _table_problems(BOOTSTRAP, recorded)
    assert _table_problems("src/vibey_tools/skills", recorded)  # the allowance is per tenant


@pytest.mark.parametrize(
    "command",
    ["echo skip mypy", "true # mypy src", "python -m mypy", "mypy --version", "ls mypy_cache"],
)
def test_the_ci_rule_rejects_a_command_that_only_mentions_mypy(command: str) -> None:
    skills = REPO / "src/vibey_tools/skills"
    assert not _checks_the_tenant(command, skills, False)


def test_the_ci_rule_accepts_a_real_invocation_and_demands_strict_when_asked() -> None:
    skills = REPO / "src/vibey_tools/skills"
    assert _checks_the_tenant("python -m mypy --strict src", skills, True)
    assert _checks_the_tenant("pip list && python -m mypy src", skills, False)
    assert not _checks_the_tenant("python -m mypy src", skills, True)


def test_a_tenant_with_no_mypy_table_has_no_way_to_pass_without_strict() -> None:
    assert _table_problems(BOOTSTRAP, None) == ["no [tool.mypy] table"]
