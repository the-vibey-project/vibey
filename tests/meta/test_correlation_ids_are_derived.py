# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""No ``correlation_id`` under ``src/vibey`` is minted with ``uuid4()``.

Issue #89's acceptance criterion, asserted rather than trusted. A random
correlation id is a delivery that cannot be joined back together, and the
failure is silent: nothing crashes, the ledger simply stops being traceable.
The check is static so a site nobody exercises still fails the build.
"""

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "vibey"

# Sites this slice could not reach, as repo-relative paths. `cli/main.py` is
# held by a concurrent branch; its `_build_spend_recorder` writes a
# `BUDGET_SPENT` draft and has `project_id` in scope, so the substitution is
# the same one-liner made everywhere else. Deleting this entry is the whole
# of that follow-up's test change -- the assertion is equality, so a fixed
# site that is left listed here fails just as loudly as a new violation.
KNOWN_REMAINING = frozenset({"cli/main.py"})


def _mints_a_random_uuid(node: ast.expr | None) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "uuid4"
        and not node.args
    )


def _violations_in(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "correlation_id":
            if _mints_a_random_uuid(node.value):
                return True
        elif isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if "correlation_id" in names and _mints_a_random_uuid(node.value):
                return True
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            if (
                isinstance(target, ast.Name)
                and target.id == "correlation_id"
                and _mints_a_random_uuid(node.value)
            ):
                return True
    return False


def test_no_correlation_id_is_minted_with_uuid4() -> None:
    offenders = {
        str(path.relative_to(SRC_ROOT))
        for path in sorted(SRC_ROOT.rglob("*.py"))
        if _violations_in(ast.parse(path.read_text(encoding="utf-8")))
    }

    assert offenders == set(KNOWN_REMAINING)


def test_the_checker_would_catch_a_planted_violation() -> None:
    """The assertion above passes trivially if the walker is broken, so plant
    each shape it is meant to catch and prove it is seen."""
    assert _violations_in(ast.parse("append(correlation_id=uuid4())"))
    assert _violations_in(ast.parse("correlation_id = uuid4()"))
    assert _violations_in(ast.parse("correlation_id: UUID = uuid4()"))
    assert not _violations_in(ast.parse("correlation_id = derive(project_id)"))
    assert not _violations_in(ast.parse("causation_id = uuid4()"))
    assert not _violations_in(ast.parse("append(correlation_id=uuid4)"))
