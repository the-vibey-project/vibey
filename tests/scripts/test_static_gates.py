# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""scripts/static_gates.py: the declared mypy trees, read from pyproject.toml and run in one place."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scripts import static_gates as sg

TABLE = """
[[tool.vibey.static_gates]]
name = "alpha"
paths = ["one", "two"]
mypy_path = "one"

[[tool.vibey.static_gates]]
name = "beta"
paths = ["three"]
mypy_path = ""
"""


def project(tmp_path: Path, text: str = TABLE) -> Path:
    path = tmp_path / "pyproject.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_entries_are_read_in_declared_order(tmp_path: Path) -> None:
    gates = sg.StaticGates(project(tmp_path))
    assert [entry.name for entry in gates.entries()] == ["alpha", "beta"]
    assert gates.entries()[0].paths == ("one", "two")


def test_the_command_is_strict_with_explicit_package_bases_then_the_paths(tmp_path: Path) -> None:
    gates = sg.StaticGates(project(tmp_path))
    assert gates.mypy_command(gates.entries()[0]) == [
        sys.executable,
        "-m",
        "mypy",
        "--strict",
        "--explicit-package-bases",
        "one",
        "two",
    ]


def test_mypypath_is_set_only_when_the_entry_declares_one(tmp_path: Path) -> None:
    gates = sg.StaticGates(project(tmp_path))
    alpha, beta = gates.entries()
    assert gates.env(alpha, {"PATH": "/bin"}) == {"PATH": "/bin", "MYPYPATH": "one"}
    assert gates.env(beta, {"PATH": "/bin", "MYPYPATH": "inherited"}) == {"PATH": "/bin"}


def test_run_returns_the_worst_exit_code_and_names_each_entry(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    codes = {"two": 0, "three": 2}
    seen: list[list[str]] = []

    def runner(argv: list[str], env: dict[str, str]) -> int:
        seen.append(argv)
        return codes[argv[-1]]

    gates = sg.StaticGates(project(tmp_path), runner=runner)
    assert gates.run() == 2
    assert len(seen) == 2
    out = capsys.readouterr().out
    assert out.index("alpha") < out.index("beta")


def test_a_killed_mypy_fails_the_gate(tmp_path: Path) -> None:
    """A signal death is a negative return code; max() against 0 would have called it green."""
    codes = {"two": -9, "three": 0}

    def runner(argv: list[str], env: dict[str, str]) -> int:
        return codes[argv[-1]]

    assert sg.StaticGates(project(tmp_path), runner=runner).run() != 0


def test_run_continues_past_a_failure_so_every_tree_is_reported(tmp_path: Path) -> None:
    calls: list[str] = []

    def runner(argv: list[str], env: dict[str, str]) -> int:
        calls.append(argv[-1])
        return 1

    assert sg.StaticGates(project(tmp_path), runner=runner).run() == 1
    assert calls == ["two", "three"]


def test_a_missing_table_is_a_clear_error(tmp_path: Path) -> None:
    gates = sg.StaticGates(project(tmp_path, "[tool.other]\nx = 1\n"))
    with pytest.raises(sg.StaticGatesMissing, match=r"tool\.vibey\.static_gates"):
        gates.entries()


def test_an_entry_without_a_name_or_paths_is_a_clear_error(tmp_path: Path) -> None:
    bad = '[[tool.vibey.static_gates]]\nname = "x"\n'
    with pytest.raises(sg.StaticGatesMissing, match="paths"):
        sg.StaticGates(project(tmp_path, bad)).entries()


def test_the_real_pyproject_declares_both_trees() -> None:
    names = [entry.name for entry in sg.StaticGates().entries()]
    assert names == ["storm-tools", "scripts"]
    scripts = sg.StaticGates().entries()[1]
    assert scripts.mypy_path == ""


def test_main_lists_names(capsys: pytest.CaptureFixture[str]) -> None:
    assert sg.main(["--list"]) == 0
    assert capsys.readouterr().out.split() == ["storm-tools", "scripts"]
