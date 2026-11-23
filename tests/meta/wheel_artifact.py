# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Building and unpacking the real wheel for the meta tests that assert on it
(tests/meta/test_wheel_ships_migrations.py, tests/meta/test_wheel_ships_default_marketplace.py).

`build_wheel` runs `uv build --wheel --offline`: the build backend comes from the cache `uv sync`
filled, and no test asks a package index. When the cache lacks it, the test is skipped with the
command that fills it; any other failure fails the test with uv's own stderr, never an opaque
`CalledProcessError`. `unpack` extracts the wheel and gives each file the mode its zip entry
records, as pip and uv do (`zipfile` alone drops them), so an executable shipped file hashes as
executable, as it would after a real install.

Module-level functions rather than a class with an interface beside it (ADR-0016): test helpers,
like tests/meta/loop_runner_facts.py, and the rule is about production code.
"""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, Final

import pytest

OFFLINE_CACHE_MISS: Final = "Packages were unavailable because the network was disabled"
"""What uv prints when an offline build needs a package its cache does not hold."""


def build_wheel(
    repo: Path,
    out: Path,
    *,
    run: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
    uv: str | None = None,
) -> Path:
    """The one `vibey_engine` wheel `uv build --offline` makes from `repo` in `out`."""
    uv = uv or shutil.which("uv")
    assert uv is not None, "uv is not on PATH; the release builds the wheel with it"
    result = run(  # a fixed argv; uv's path comes from shutil.which
        [uv, "build", "--wheel", "--offline", "--out-dir", str(out), str(repo)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        if OFFLINE_CACHE_MISS in result.stderr:
            pytest.skip(
                "uv's cache does not hold the wheel's build backend and the build may not use the "
                "network: run `uv sync --extra dev` once, then rerun"
            )
        pytest.fail(f"`uv build --offline` exited {result.returncode}:\n{result.stderr}")
    built = sorted(out.glob("vibey_engine-*.whl"))
    assert len(built) == 1, f"expected one vibey_engine wheel, found {built}"
    return built[0]


def unpack(wheel: Path, dest: Path) -> Path:
    """`wheel` extracted under `dest`, each file with the permission bits its entry records."""
    with zipfile.ZipFile(wheel) as archive:
        for info in archive.infolist():
            extracted = Path(archive.extract(info, dest))
            mode = (info.external_attr >> 16) & 0o777
            if mode and not info.is_dir():
                extracted.chmod(mode)
    return dest
