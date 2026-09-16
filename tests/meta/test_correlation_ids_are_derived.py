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

# Sites this slice could not reach, as repo-relative path -> how many. `cli/main.py`
# is held by a concurrent branch; its `_build_spend_recorder` writes a
# `BUDGET_SPENT` draft and has `project_id` in scope, so the substitution is
# the same one-liner made everywhere else. Deleting this entry is the whole
# of that follow-up's test change -- the assertion is equality, so a fixed
# site that is left listed here fails just as loudly as a new violation.
#
# The COUNT is what makes the guard total, and a set of paths would not be.
# Whitelisting a file rather than a site means a second `uuid4()` added to an
# already-listed file lands inside the exemption and the assertion still holds:
# the check would report "every site is derived" while two were not. Counting
# closes that, so the exemption covers exactly the one occurrence examined here
# and nothing that arrives beside it later.
KNOWN_REMAINING = {"cli/main.py": 1}


def _mints_a_random_uuid(node: ast.expr | None) -> bool:
    """True for a call that mints a fresh random uuid, however it is spelled.

    Both import styles have to be caught or the check is advisory: the bare
    `uuid4()` of `from uuid import uuid4`, and the dotted `uuid.uuid4()` of
    `import uuid`. Matching only the first would let the second through, and
    the failure this guards is silent -- an untraceable delivery, with nothing
    crashing to announce it. The attribute form is matched on its tail, so
    an aliased `import uuid as u` is caught too.
    """
    if not isinstance(node, ast.Call) or node.args or node.keywords:
        return False
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == "uuid4"
    return isinstance(func, ast.Attribute) and func.attr == "uuid4"


def _violations_in(tree: ast.AST) -> int:
    """How many minted correlation ids this module contains, not merely whether.

    A count rather than a flag because the exemption below is per occurrence: a
    file is never wholesale forgiven, only the exact number of sites examined
    when it was listed. Returning on the first hit would make a second violation
    in an exempt file invisible.
    """
    found = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "correlation_id":
            found += _mints_a_random_uuid(node.value)
        elif isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            found += "correlation_id" in names and _mints_a_random_uuid(node.value)
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            found += (
                isinstance(target, ast.Name)
                and target.id == "correlation_id"
                and _mints_a_random_uuid(node.value)
            )
    return found


def test_no_correlation_id_is_minted_with_uuid4() -> None:
    offenders = {
        str(path.relative_to(SRC_ROOT)): count
        for path in sorted(SRC_ROOT.rglob("*.py"))
        if (count := _violations_in(ast.parse(path.read_text(encoding="utf-8"))))
    }

    assert offenders == KNOWN_REMAINING


def test_the_checker_would_catch_a_planted_violation() -> None:
    """The assertion above passes trivially if the walker is broken, so plant
    each shape it is meant to catch and prove it is seen."""
    assert _violations_in(ast.parse("append(correlation_id=uuid4())"))
    assert _violations_in(ast.parse("correlation_id = uuid4()"))
    assert _violations_in(ast.parse("correlation_id: UUID = uuid4()"))
    assert not _violations_in(ast.parse("correlation_id = derive(project_id)"))
    assert _violations_in(ast.parse("append(correlation_id=uuid.uuid4())"))
    assert _violations_in(ast.parse("correlation_id = uuid.uuid4()"))
    assert _violations_in(ast.parse("correlation_id: UUID = u.uuid4()"))
    assert not _violations_in(ast.parse("causation_id = uuid4()"))
    assert not _violations_in(ast.parse("causation_id = uuid.uuid4()"))
    assert not _violations_in(ast.parse("append(correlation_id=uuid4)"))
    assert not _violations_in(ast.parse("append(correlation_id=uuid.uuid4)"))
    assert not _violations_in(ast.parse("correlation_id = uuid5(ns, name)"))


def test_the_exemption_covers_one_site_and_not_the_whole_file() -> None:
    """The hole a set of filenames leaves open, closed and proved shut.

    Whitelisting `cli/main.py` by NAME would forgive whatever else lands in it:
    a second minted id inside an exempt file keeps `offenders` identical, and a
    guard that claims to check every write site would pass while two were wrong.
    Counting is what makes the exemption cover exactly the occurrence examined.
    """
    one = "append(correlation_id=uuid4())"
    assert _violations_in(ast.parse(one)) == 1
    assert _violations_in(ast.parse(one + "\n" + one)) == 2
    # Mixed spellings are counted too -- one shape must not mask another.
    assert _violations_in(ast.parse(one + "\ncorrelation_id = uuid.uuid4()")) == 2
    # And the listed count is the real one, so the exemption cannot drift silently.
    assert KNOWN_REMAINING == {"cli/main.py": 1}
