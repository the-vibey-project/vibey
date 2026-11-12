# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Run `mypy --strict` over every tree declared in `[[tool.vibey.static_gates]]`.

    python3 scripts/static_gates.py          # check every declared tree, exit with the worst code
    python3 scripts/static_gates.py --list   # print the declared names

The list lives in pyproject.toml so that the `lint` job, this script and the every-Python-file
census (tests/meta/test_every_python_file_is_gated.py) read one declaration (sub-doctrine 12.c).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.interfaces.static_gates_interface import StaticGateEntryInterface
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from interfaces.static_gates_interface import (  # type: ignore[import-not-found,no-redef]
        StaticGateEntryInterface,
    )

REPO = Path(__file__).resolve().parents[1]
Runner = Callable[[list[str], dict[str, str]], int]


class StaticGatesMissing(ValueError):
    """The declaration is absent or incomplete; the message says what to add."""


@dataclass(frozen=True, slots=True)
class StaticGateEntry:
    """One declared tree."""

    name: str
    paths: tuple[str, ...]
    mypy_path: str


class StaticGates:
    """The declared trees, the mypy command for each, and a run over all of them."""

    def __init__(self, pyproject: Path = REPO / "pyproject.toml", runner: Runner | None = None):
        self.pyproject = pyproject
        self.runner = runner or self._subprocess

    @staticmethod
    def _subprocess(argv: list[str], env: dict[str, str]) -> int:
        return subprocess.run(argv, env=env, cwd=REPO, check=False).returncode

    def entries(self) -> list[StaticGateEntryInterface]:
        table = tomllib.loads(self.pyproject.read_text(encoding="utf-8"))
        rows = table.get("tool", {}).get("vibey", {}).get("static_gates")
        if not rows:
            raise StaticGatesMissing(
                f"{self.pyproject} declares no [[tool.vibey.static_gates]] table"
            )
        entries: list[StaticGateEntryInterface] = []
        for row in rows:
            name = row.get("name")
            paths = row.get("paths")
            if not name or not paths:
                raise StaticGatesMissing(
                    f"a [[tool.vibey.static_gates]] entry needs a name and paths: {row!r}"
                )
            entries.append(StaticGateEntry(name, tuple(paths), row.get("mypy_path", "")))
        return entries

    def mypy_command(self, entry: StaticGateEntryInterface) -> list[str]:
        return ["mypy", "--strict", "--explicit-package-bases", *entry.paths]

    def env(self, entry: StaticGateEntryInterface, base: Mapping[str, str]) -> dict[str, str]:
        env = {key: value for key, value in base.items() if key != "MYPYPATH"}
        if entry.mypy_path:
            env["MYPYPATH"] = entry.mypy_path
        return env

    def run(self) -> int:
        worst = 0
        for entry in self.entries():
            print(f"== {entry.name}", flush=True)
            code = self.runner(self.mypy_command(entry), self.env(entry, os.environ))
            worst = max(worst, code)
        return worst


# A bare function because it is this script's `__main__` entry point (ADR-0016).
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--list", action="store_true", help="print the declared names")
    args = parser.parse_args(argv)
    gates = StaticGates()
    try:
        if args.list:
            for entry in gates.entries():
                print(entry.name)
            return 0
        return gates.run()
    except StaticGatesMissing as error:
        print(error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
