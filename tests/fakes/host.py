# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Fake command executor and time utilities used in tests.

The fake executor simulates ``shutil.which`` and ``subprocess.run`` for
unit‑tests of the host package runner.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from vibey.infrastructure.host_packages import CommandResult


@dataclass
class FakeCommandExecutor:
    """Very small stub for testing package runner behaviour.

    Parameters
    ----------
    on_path:
        Iterable of command names that should report as present on PATH.
    responses:
        Mapping from argv prefix to a ``CommandResult`` or a ``list`` of them.  The
        longest matching prefix wins.
    default:
        ``CommandResult`` to return when no matching response is found.
    """

    on_path: Iterable[str]
    responses: dict[tuple[str, ...], CommandResult | list[CommandResult]] | None = None
    default: CommandResult = CommandResult(0)

    calls: list[tuple[str, ...]] = None

    def __post_init__(self) -> None:
        self.calls = []
        self._responses = {}
        if self.responses:
            for key, value in self.responses.items():
                if isinstance(value, list):
                    self._responses[tuple(key)] = list(value)
                else:
                    self._responses[tuple(key)] = [value]

    def which(self, name: str) -> str | None:
        return f"/usr/bin/{name}" if name in self.on_path else None

    def run(self, argv: tuple[str, ...], *, timeout: float = 600.0) -> CommandResult:
        self.calls.append(argv)
        # find longest matching prefix
        best: list[CommandResult] | None = None
        for prefix, res in self._responses.items():
            if argv[: len(prefix)] == prefix and (best is None or len(prefix) > len(best)):
                best = res
        if best is None:
            return self.default
        # consume one
        result = best.pop(0)
        if not best:
            best.append(result)
        return result


@dataclass
class FakeTime:
    """Fake time keeping track of monotonic clock and sleeps."""

    now: float = 0.0
    sleeps: list[float] = None

    def __post_init__(self) -> None:
        self.sleeps = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds
        self.sleeps.append(seconds)
