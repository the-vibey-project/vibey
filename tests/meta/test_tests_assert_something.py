# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every test asserts something: an AST census of `tests/**` ratcheted down in a TOML file.

A test that calls the code and checks nothing passes whatever the code does, so it is
coverage without evidence. Definition (the census applies exactly this): a test function
counts as checked if it has an `assert` statement, or a `with` whose context is
`pytest.raises`, `pytest.warns` or `pytest.fail`-like, or any call whose function name starts
with `assert`, `expect`, `verify` or `check` or contains `assert`, or is `fail`, `skip`,
`xfail` or `approx`. A test function is a `test*` function defined at module level or directly
in a class, the places pytest collects from; helpers nested inside a test are part of it.

The ones with no check are recorded in `tests/meta/assertion_free_tests.toml` as
`file::name`, each with a reason, and the list can only shrink: a new one fails, and so does a
recorded one that now has a check or is gone, so the entry leaves in the same change that fixes
it. Where "does not raise" is the whole point, assert the return value (`is None`) instead of
recording an entry.

Module-level test functions rather than a class with an interface beside it (ADR-0016): pytest
collects `test_*` functions, and the rule is about production code. The census itself is a
class, so it can be run on synthetic source.
"""

from __future__ import annotations

import ast
import subprocess
import tomllib
from collections.abc import Iterator
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TESTS = REPO / "tests"
BASELINE = Path(__file__).with_name("assertion_free_tests.toml")
CHECK_PREFIXES = ("assert", "expect", "verify", "check")
CHECK_NAMES = frozenset({"fail", "skip", "xfail", "approx"})
CHECK_CONTEXTS = ("raises", "warns", "fail")


class AssertionCensus:
    """Which `test*` functions in a source file have no check at all."""

    @staticmethod
    def _called_name(call: ast.Call) -> str:
        func = call.func
        if isinstance(func, ast.Attribute):
            return func.attr
        return func.id if isinstance(func, ast.Name) else ""

    @classmethod
    def _is_check(cls, node: ast.AST) -> bool:
        if isinstance(node, ast.Assert):
            return True
        if isinstance(node, ast.With | ast.AsyncWith):
            return any(
                word in ast.unparse(item.context_expr)
                for item in node.items
                for word in CHECK_CONTEXTS
            )
        if isinstance(node, ast.Call):
            name = cls._called_name(node)
            lowered = name.lower()
            return lowered.startswith(CHECK_PREFIXES) or "assert" in lowered or name in CHECK_NAMES
        return False

    @classmethod
    def has_a_check(cls, function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        return any(cls._is_check(node) for node in ast.walk(function))

    @staticmethod
    def collected(tree: ast.Module) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
        """`test*` functions at module level or directly in a class: what pytest collects."""
        scopes: list[list[ast.stmt]] = [tree.body]
        scopes.extend(node.body for node in tree.body if isinstance(node, ast.ClassDef))
        for body in scopes:
            for node in body:
                if isinstance(
                    node, ast.FunctionDef | ast.AsyncFunctionDef
                ) and node.name.startswith("test"):
                    yield node

    @classmethod
    def unchecked(cls, source: str) -> list[str]:
        return [fn.name for fn in cls.collected(ast.parse(source)) if not cls.has_a_check(fn)]

    @staticmethod
    def tracked_python(root: Path) -> list[Path]:
        """The git-tracked `.py` files under `root`, so an untracked scratch file cannot fail
        a local run (the single-source guard walks the same list)."""
        listed = subprocess.run(
            ["git", "ls-files", "-z", "--", str(root)],
            cwd=REPO,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.split("\0")
        return sorted(
            REPO / name for name in listed if name.endswith(".py") and (REPO / name).is_file()
        )

    @classmethod
    def census(cls, root: Path) -> tuple[int, list[str]]:
        """(test functions seen, `file::name` of each that checks nothing), one parse per file."""
        seen = 0
        found: list[str] = []
        for path in cls.tracked_python(root):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            relative = path.relative_to(REPO).as_posix()
            for function in cls.collected(tree):
                seen += 1
                if not cls.has_a_check(function):
                    found.append(f"{relative}::{function.name}")
        return seen, found


def recorded() -> dict[str, str]:
    table = tomllib.loads(BASELINE.read_text(encoding="utf-8"))
    return {str(key): str(reason) for key, reason in table.get("entries", {}).items()}


def test_every_test_asserts_something_or_is_recorded_with_a_reason() -> None:
    seen, found = AssertionCensus.census(TESTS)
    new = sorted(set(found) - set(recorded()))
    assert seen > 6000, f"the census saw only {seen} tests; is the walk broken?"
    assert new == [], (
        "these tests call code and check nothing: give each an assertion (a return value, "
        f"`is None`, a recorded call), or record it with a reason in {BASELINE.name}: {new}"
    )


def test_a_recorded_assertion_free_test_that_now_checks_something_is_removed() -> None:
    _, found = AssertionCensus.census(TESTS)
    stale = sorted(set(recorded()) - set(found))
    assert stale == [], f"delete these from {BASELINE.name}, they are fixed or gone: {stale}"


def test_every_recorded_assertion_free_test_has_a_reason() -> None:
    blank = sorted(key for key, reason in recorded().items() if not reason.strip())
    assert blank == []


def test_the_definition_counts_what_it_says_it_counts() -> None:
    checked = """
def test_a(): assert 1
def test_b():
    with pytest.raises(ValueError): f()
def test_c(): assert_clean(x)
def test_d(): expect_ok(x)
def test_e(): self.verify_it()
def test_f(): check_all()
def test_g(): helper.assertEqual(1, 1)
def test_h(): pytest.fail("no")
def test_i(): pytest.skip("no")
def test_j(): assert abs(x - 1) == pytest.approx(0)
async def test_k(): await assert_never_killed(r)
class TestK:
    def test_l(self): self.assertTrue(x)
    def test_m(self):
        with pytest.warns(UserWarning): f()
"""
    assert AssertionCensus.unchecked(checked) == []


def test_the_definition_flags_what_it_says_it_flags() -> None:
    bare = """
def test_a(): f()
def test_b():
    with open("x"): f()
def test_c():
    def helper(): return 1
    helper()
async def test_d(): await f()
def test_e(): _never_killed(r)
class TestK:
    def test_f(self): self.run()
def helper_not_a_test(): f()
"""
    assert AssertionCensus.unchecked(bare) == [
        "test_a",
        "test_b",
        "test_c",
        "test_d",
        "test_e",
        "test_f",
    ]


def test_a_nested_function_named_test_is_not_a_collected_test() -> None:
    nested = """
def test_outer():
    def tested(): return 1
    assert tested()
"""
    assert AssertionCensus.unchecked(nested) == []
