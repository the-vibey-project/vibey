# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The `vibey` the web tools run: the one installed beside this runner (SP-LOOPS Phase 6)."""

from pathlib import Path

from qwenloop.infrastructure.interfaces import VibeyCommandInterface
from qwenloop.infrastructure.vibey_command import VIBEY_COMMAND, VibeyCommand


def _script(folder: Path, mode: int) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    script = folder / "vibey"
    script.write_text("#!/bin/sh\n")
    script.chmod(mode)
    return script


def test_it_meets_its_seam() -> None:
    assert isinstance(VIBEY_COMMAND, VibeyCommandInterface)


def test_the_vibey_beside_this_python_wins_over_path(tmp_path: Path) -> None:
    script = _script(tmp_path / "bin", 0o755)
    command = VibeyCommand(executable=str(tmp_path / "bin" / "python"), which=lambda _: "/other")
    assert command.resolve() == str(script)


def test_a_sibling_that_cannot_run_is_passed_over_for_path_then_the_bare_name(
    tmp_path: Path,
) -> None:
    _script(tmp_path / "bin", 0o644)
    python = str(tmp_path / "bin" / "python")
    assert VibeyCommand(executable=python, which=lambda _: "/other/vibey").resolve() == (
        "/other/vibey"
    )
    assert VibeyCommand(executable=python, which=lambda _: None).resolve() == "vibey"


def test_a_sibling_folder_is_not_a_command(tmp_path: Path) -> None:
    (tmp_path / "bin" / "vibey").mkdir(parents=True)
    python = str(tmp_path / "bin" / "python")
    assert VibeyCommand(executable=python, which=lambda _: None).resolve() == "vibey"
