# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The helpers the wheel tests share: an offline build that says why it failed, and an unpack
that keeps each file's mode the way an installer does (SP-LOOPS Task 6 review 2, should-fix a
and c).

Module-level test functions rather than a class with an interface beside it (ADR-0016),
following tests/meta/test_shipped_trees_are_reachable.py: pytest collects `test_*` functions,
and the rule is about production code.
"""

from __future__ import annotations

import stat
import subprocess
import zipfile
from collections.abc import Sequence
from pathlib import Path

import pytest

from tests.meta.wheel_artifact import OFFLINE_CACHE_MISS, build_wheel, unpack


def _zip(path: Path, entries: dict[str, int]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, mode in entries.items():
            info = zipfile.ZipInfo(name)
            info.external_attr = mode << 16
            archive.writestr(info, f"{name}\n")
    return path


def test_unpacking_keeps_the_mode_bits_an_installer_keeps(tmp_path: Path) -> None:
    wheel = _zip(
        tmp_path / "x.whl",
        {"pkg/run.sh": 0o100755, "pkg/data.txt": 0o100644, "pkg/plain.txt": 0},
    )
    out = unpack(wheel, tmp_path / "site")
    assert stat.S_IMODE((out / "pkg/run.sh").stat().st_mode) == 0o755
    assert stat.S_IMODE((out / "pkg/data.txt").stat().st_mode) == 0o644
    assert (out / "pkg/plain.txt").read_text() == "pkg/plain.txt\n"  # no mode recorded: default


class _Run:
    """Stands in for `subprocess.run`: records the argv, and makes a wheel or fails as told."""

    def __init__(self, returncode: int = 0, stderr: str = "") -> None:
        self.returncode = returncode
        self.stderr = stderr
        self.argv: list[str] = []

    def __call__(self, argv: Sequence[str], **_: object) -> subprocess.CompletedProcess[str]:
        self.argv = list(argv)
        if self.returncode == 0:
            out = Path(argv[argv.index("--out-dir") + 1])
            (out / "vibey_engine-0.0.0-py3-none-any.whl").write_bytes(b"")
        return subprocess.CompletedProcess(argv, self.returncode, "", self.stderr)


def test_the_build_is_offline_and_returns_the_one_wheel(tmp_path: Path) -> None:
    run = _Run()
    wheel = build_wheel(tmp_path, tmp_path, run=run, uv="/bin/uv")
    assert wheel.name == "vibey_engine-0.0.0-py3-none-any.whl"
    assert run.argv[:4] == ["/bin/uv", "build", "--wheel", "--offline"]


def test_a_cold_cache_skips_with_the_command_that_warms_it(tmp_path: Path) -> None:
    run = _Run(2, f"error: hatchling not found\nhint: {OFFLINE_CACHE_MISS} from the cache.\n")
    with pytest.raises(pytest.skip.Exception, match="uv sync"):
        build_wheel(tmp_path, tmp_path, run=run, uv="/bin/uv")


def test_any_other_build_failure_shows_uv_s_own_words(tmp_path: Path) -> None:
    run = _Run(1, "error: pyproject.toml is not valid TOML at line 7\n")
    with pytest.raises(pytest.fail.Exception, match="not valid TOML at line 7"):
        build_wheel(tmp_path, tmp_path, run=run, uv="/bin/uv")
