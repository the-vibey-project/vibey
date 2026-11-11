# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""No in-process test waits on the real clock for more than a blink (ratcheted).

A `time.sleep(2)` in a test is two seconds on every run, on every runner, for ever. The
census is an AST walk over `tests/**`: it finds each `time.sleep(<literal>)` and
`asyncio.sleep(<literal>)` call whose literal is a number greater than 0.05. Being an AST
walk, it never sees a sleep that sits inside a string literal: the script text a test hands to
a subprocess (`python -c "import time; time.sleep(30)"`) is data, not a wait in this process.
Fake clocks (`clock.sleep(...)`) and non-literal arguments are not real waits either.

What remains is recorded in `tests/meta/real_sleeps.toml` as `file::enclosing function` (a
module-level sleep is `file::<module>`) with a `count` and the `reason` the wait is real, so an
edit above a sleep does not disturb the entry. The counts can only fall: a new sleep or a higher
count fails, and so does a recorded count above what is there now, so the entry is lowered or
removed in the same change that removes the sleep. Where the
code under test takes an injected clock or sleeper, inject it instead of waiting.

Module-level test functions rather than a class with an interface beside it (ADR-0016); the
census itself is a class, so it can be run on synthetic source.
"""

from __future__ import annotations

import ast
import subprocess
import tomllib
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TESTS = REPO / "tests"
BASELINE = Path(__file__).with_name("real_sleeps.toml")
MODULES = frozenset({"time", "asyncio"})
THRESHOLD_SECONDS = 0.05


class SleepCensus:
    """Where a source file waits on the real clock for longer than the threshold."""

    @staticmethod
    def _seconds(call: ast.Call) -> float | None:
        """The literal wait of a `time.sleep(n)` / `asyncio.sleep(n)` call, else None."""
        func = call.func
        if not (
            isinstance(func, ast.Attribute)
            and func.attr == "sleep"
            and isinstance(func.value, ast.Name)
            and func.value.id in MODULES
            and call.args
        ):
            return None
        first = call.args[0]
        if not isinstance(first, ast.Constant) or isinstance(first.value, bool):
            return None
        value = first.value
        return float(value) if isinstance(value, int | float) else None

    @classmethod
    def sleeps(cls, source: str) -> Counter[str]:
        """Sleeps over the threshold by enclosing scope (dotted class/def names, or `<module>`)."""
        found: Counter[str] = Counter()

        def walk(node: ast.AST, scope: tuple[str, ...]) -> None:
            for child in ast.iter_child_nodes(node):
                inner = scope
                if isinstance(child, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
                    inner = (*scope, child.name)
                if (
                    isinstance(child, ast.Call)
                    and (seconds := cls._seconds(child)) is not None
                    and seconds > THRESHOLD_SECONDS
                ):
                    found[".".join(scope) or "<module>"] += 1
                walk(child, inner)

        walk(ast.parse(source), ())
        return found

    @staticmethod
    def tracked_python(root: Path) -> list[Path]:
        """The git-tracked `.py` files under `root`, so an untracked scratch file cannot fail
        a local run."""
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
    def census(cls, root: Path) -> Counter[str]:
        """`file::scope` -> number of such sleeps under `root`, one parse per file."""
        found: Counter[str] = Counter()
        for path in cls.tracked_python(root):
            relative = path.relative_to(REPO).as_posix()
            for scope, count in cls.sleeps(path.read_text(encoding="utf-8")).items():
                found[f"{relative}::{scope}"] += count
        return found


def recorded() -> dict[str, tuple[int, str]]:
    """`file::scope` -> (count, reason)."""
    table = tomllib.loads(BASELINE.read_text(encoding="utf-8"))
    return {
        str(key): (int(entry["count"]), str(entry["reason"]))
        for key, entry in table.get("entries", {}).items()
    }


def test_no_new_real_sleep_over_the_threshold_in_a_test() -> None:
    allowed = {key: count for key, (count, _) in recorded().items()}
    more = sorted(key for key, n in SleepCensus.census(TESTS).items() if n > allowed.get(key, 0))
    assert more == [], (
        f"these tests wait on the real clock for over {THRESHOLD_SECONDS}s: inject the clock or "
        f"sleeper the code under test takes, or record each with a count and reason in "
        f"{BASELINE.name}: {more}"
    )


def test_a_recorded_sleep_count_above_what_is_there_now_is_lowered_or_removed() -> None:
    actual = SleepCensus.census(TESTS)
    stale = sorted(key for key, (count, _) in recorded().items() if count > actual.get(key, 0))
    assert stale == [], f"lower or delete these in {BASELINE.name}, the sleeps are gone: {stale}"


def test_every_recorded_sleep_has_a_reason_and_a_count() -> None:
    bad = sorted(
        key for key, (count, reason) in recorded().items() if count < 1 or not reason.strip()
    )
    assert bad == []


def test_a_sleep_is_keyed_by_its_enclosing_scope_so_an_edit_above_it_changes_nothing() -> None:
    source = "\n".join(
        [
            "import time",
            "time.sleep(1)",
            "class TestA:",
            "    def test_b(self):",
            "        def helper():",
            "            time.sleep(2)",
            "        time.sleep(3)",
            "        time.sleep(4)",
        ]
    )
    shifted = "\n\n\n" + source
    expected = {"<module>": 1, "TestA.test_b.helper": 1, "TestA.test_b": 2}
    assert dict(SleepCensus.sleeps(source)) == expected
    assert dict(SleepCensus.sleeps(shifted)) == expected


def test_the_census_sees_a_real_wait_and_ignores_script_text_and_small_waits() -> None:
    source = "\n".join(
        [
            "import asyncio",
            "import time",
            "",
            "def test_a():",
            "    time.sleep(1.1)",  # line 5: counted
            "    time.sleep(0.05)",
            "    time.sleep(0.06)",  # line 7: counted
            "    time.sleep(delay)",
            "    time.sleep(True)",
            "    clock.sleep(30)",
            "    run(['python', '-c', 'import time; time.sleep(30)'])",
            "    script = 'time.sleep(5)'",
            "",
            "async def test_b():",
            "    await asyncio.sleep(2)",  # line 15: counted
            "    await asyncio.sleep(0.01)",
            "    await asyncio.sleep()",
        ]
    )
    assert dict(SleepCensus.sleeps(source)) == {"test_a": 2, "test_b": 1}
