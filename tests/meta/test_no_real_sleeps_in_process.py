# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""No in-process test waits on the real clock for more than a blink (ratcheted).

A `time.sleep(2)` in a test is two seconds on every run, on every runner, for ever. The
census is an AST walk over `tests/**`: it finds each `time.sleep(<literal>)` and
`asyncio.sleep(<literal>)` call whose literal is a number greater than 0.05. Being an AST
walk, it never sees a sleep that sits inside a string literal: the script text a test hands to
a subprocess (`python -c "import time; time.sleep(30)"`) is data, not a wait in this process.
Fake clocks (`clock.sleep(...)`) and non-literal arguments are not real waits either.

What remains is recorded in `tests/meta/real_sleeps.toml` as `file:line`, each with the reason
the wait is real, and the list can only shrink: a new sleep fails, and so does a recorded one
that is gone or moved, so the entry leaves in the same change that removes the sleep. Where the
code under test takes an injected clock or sleeper, inject it instead of waiting.

Module-level test functions rather than a class with an interface beside it (ADR-0016); the
census itself is a class, so it can be run on synthetic source.
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

TESTS = Path(__file__).resolve().parents[1]
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
    def lines(cls, source: str) -> list[int]:
        """Line numbers of the sleeps over the threshold."""
        return sorted(
            node.lineno
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Call)
            and (seconds := cls._seconds(node)) is not None
            and seconds > THRESHOLD_SECONDS
        )

    @classmethod
    def census(cls, root: Path) -> list[str]:
        """`file:line` of every such sleep under `root`, one parse per file."""
        found: list[str] = []
        for path in sorted(root.rglob("*.py")):
            relative = f"tests/{path.relative_to(root).as_posix()}"
            found.extend(
                f"{relative}:{line}" for line in cls.lines(path.read_text(encoding="utf-8"))
            )
        return found


def recorded() -> dict[str, str]:
    table = tomllib.loads(BASELINE.read_text(encoding="utf-8"))
    return {str(key): str(reason) for key, reason in table.get("entries", {}).items()}


def test_no_new_real_sleep_over_the_threshold_in_a_test() -> None:
    new = sorted(set(SleepCensus.census(TESTS)) - set(recorded()))
    assert new == [], (
        f"these tests wait on the real clock for over {THRESHOLD_SECONDS}s: inject the clock or "
        f"sleeper the code under test takes, or record each with a reason in {BASELINE.name}: {new}"
    )


def test_a_recorded_sleep_that_is_gone_or_moved_is_removed() -> None:
    stale = sorted(set(recorded()) - set(SleepCensus.census(TESTS)))
    assert stale == [], f"delete or re-point these in {BASELINE.name}: {stale}"


def test_every_recorded_sleep_has_a_reason() -> None:
    blank = sorted(key for key, reason in recorded().items() if not reason.strip())
    assert blank == []


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
    assert SleepCensus.lines(source) == [5, 7, 15]
