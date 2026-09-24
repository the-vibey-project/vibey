# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A hung test must fail loudly and name itself, in both suites that run on push.

On 2026-09-24 one push's pytest (8 xdist workers) sat at 0% CPU for 39 minutes, every
worker asleep, while it held the storm's shared push lock; every other push queued behind
it. A human killed it. Nothing recorded which test hung, so the hang is still unexplained.

Three layers now stand between a stuck test and a stuck storm, and these tests pin the two
that live in pytest's own configuration:

  * `faulthandler_timeout`: a test still running after that many seconds has every
    thread's traceback dumped, once, while it keeps running;
  * `timeout` (pytest-timeout): at that many seconds the test FAILS, named, with its stack,
    and the suite carries on;
  * the storm's push-gate reaper (docs/plans/qwenstorm-3.0.0/tools/push_gate.py) is the
    outer backstop for a hang no signal inside pytest can reach.

A setting that quietly disappears in a pyproject edit would return the suite to "hangs
forever, says nothing", so the settings, the dependency and the live plugin are all held
here. The values are overridable on the command line (`--timeout=N`, `-o
faulthandler_timeout=N`); only their presence and their order are pinned.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import time
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SUITES = {
    "vibey": ROOT / "pyproject.toml",
    "vibey-gh": ROOT / "src/vibey_tools/gh/pyproject.toml",
}


def _ini(pyproject: Path) -> dict[str, object]:
    return tomllib.loads(pyproject.read_text(encoding="utf-8"))["tool"]["pytest"]["ini_options"]


@pytest.mark.parametrize("suite", sorted(SUITES))
def test_every_suite_declares_a_per_test_timeout_and_a_stall_dump(suite: str) -> None:
    ini = _ini(SUITES[suite])
    timeout = int(str(ini.get("timeout", 0)))
    dump = int(str(ini.get("faulthandler_timeout", 0)))
    assert timeout > 0, f"{suite}: [tool.pytest.ini_options] timeout is missing"
    assert dump > 0, f"{suite}: [tool.pytest.ini_options] faulthandler_timeout is missing"
    # The dump comes first: it is the evidence, and the timeout ends the test that made it.
    assert dump < timeout, f"{suite}: the stall dump ({dump}s) must precede the timeout"
    # Generous, not tight: the longest honest test in either suite is well under a minute,
    # and a limit that fires on a slow CI runner is a flaky test, not a guard.
    assert timeout >= 120, f"{suite}: a {timeout}s per-test limit would fire on a slow runner"


@pytest.mark.parametrize("suite", sorted(SUITES))
def test_every_suite_installs_the_timeout_plugin_it_configures(suite: str) -> None:
    project = tomllib.loads(SUITES[suite].read_text(encoding="utf-8"))["project"]
    dev = project["optional-dependencies"]["dev"]
    assert any(dep.startswith("pytest-timeout") for dep in dev), (
        f"{suite}: `timeout` is configured but pytest-timeout is not in the dev extra, so the "
        "setting is an unknown ini key and nothing enforces it"
    )


def _suite(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a throwaway suite whose one test sleeps far past a one-second limit."""
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (tmp_path / "test_sleeper.py").write_text(
        textwrap.dedent(
            """
            import time

            def test_that_sleeps_forever():
                time.sleep(120)
            """
        ),
        encoding="utf-8",
    )
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "--timeout=1", *args],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=90,
    )


def test_the_timeout_plugin_is_live_and_names_the_hung_test(tmp_path: Path) -> None:
    started = time.monotonic()
    done = _suite(tmp_path, "-p", "no:xdist")
    output = done.stdout + done.stderr
    assert done.returncode == 1, output
    assert "Timeout" in output, output
    assert "test_that_sleeps_forever" in output, output
    assert time.monotonic() - started < 60, "the one-second limit did not end the test"


def test_the_timeout_names_the_hung_test_under_xdist(tmp_path: Path) -> None:
    """The repository runs its suite with `-n auto`; the guard must hold inside a worker."""
    done = _suite(tmp_path, "-n", "2")
    output = done.stdout + done.stderr
    assert done.returncode == 1, output
    assert "Timeout" in output, output
    assert "FAILED test_sleeper.py::test_that_sleeps_forever" in output, output


def test_the_root_suite_dumps_every_stack_on_sigusr1_into_the_stacks_directory(
    tmp_path: Path,
) -> None:
    """The push-gate reaper asks a hung suite for its stacks before it kills it.

    Where the dump goes matters as much as that it happens: a worker's stderr is captured by
    pre-commit, which the reaper is about to kill, so a dump to stderr would be lost with it.
    `VIBEY_PYTEST_STACKS_DIR` (set by `push_gate.py run`) sends it to a file per process.
    """
    stacks = tmp_path / "stacks"
    probe = textwrap.dedent(
        """
        import os, signal, time
        from tests.conftest import _arm_stack_dump
        _arm_stack_dump()
        os.kill(os.getpid(), signal.SIGUSR1)
        time.sleep(0.5)
        print("still alive")
        """
    )
    done = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=ROOT,
        env={**os.environ, "VIBEY_PYTEST_STACKS_DIR": str(stacks)},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    # The dump is evidence, not a kill: the process carries on.
    assert "still alive" in done.stdout
    dumps = list(stacks.glob("pytest-*.stacks"))
    assert len(dumps) == 1, dumps
    text = dumps[0].read_text(encoding="utf-8")
    assert "Current thread" in text or "Thread 0x" in text, text
