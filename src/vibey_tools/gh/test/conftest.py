# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Shared fixtures, and the one gate on tests that leave the machine.

The suite must behave the same on a laptop and inside GitHub Actions. Actions exports a
number of variables that the code under test reads, and a test that silently changes
behaviour because of one of them is worse than a failing test: it hides a branch and,
in this case, writes into the real job summary.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

# Variables Actions sets that this tool reads. Cleared for every test; a test that wants
# one sets it explicitly, which also documents that it is what is under test.
_ACTIONS_ENV = ("GITHUB_STEP_SUMMARY", "GITHUB_RUN_NUMBER", "GITHUB_OUTPUT")

# The single switch for every test that needs an index, a remote, or any other thing on
# the far side of a socket. One mechanism, not two: a test declares itself with
# `@pytest.mark.network`, and this hook is what honours VIBEY_GH_NETWORK_TESTS. Off by
# default, so a plain offline `pytest` still enforces the package's 100% branch floor and
# no caller has to know a flag; a runner with an index sets the variable and selects the
# marked tests with `-m network`.
_NETWORK_ENV = "VIBEY_GH_NETWORK_TESTS"


# Module-level rather than a class (vibey ADR-0016) because pytest resolves its hooks by
# name at conftest module scope; a method is never called.
def pytest_collection_modifyitems(config, items):
    if os.environ.get(_NETWORK_ENV) == "1":
        return
    skip = pytest.mark.skip(reason=f"leaves the machine; set {_NETWORK_ENV}=1 to run")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def _no_ambient_actions_env(monkeypatch):
    for name in _ACTIONS_ENV:
        monkeypatch.delenv(name, raising=False)


class _NeverResting:
    """A Sabbath guard that never holds, so a test's outcome does not depend on the day of
    the week it runs on. Tests of the Sabbath itself opt out with `@pytest.mark.sabbath`."""

    def hold(self, at=None):
        return None


# Module-level rather than a class (vibey ADR-0016): pytest resolves fixtures by name.
@pytest.fixture(autouse=True)
def _weekday_independent(request, monkeypatch):
    if request.node.get_closest_marker("sabbath") is None:
        monkeypatch.setattr("vibey_gh.cli._sabbath_guard", lambda cfg: _NeverResting())


# Module-level rather than a class (vibey ADR-0016) because pytest resolves a fixture by
# name at conftest module scope.
@pytest.fixture
def scripted_gh(tmp_path: Path, monkeypatch) -> Path:
    """A real `gh` executable on PATH that replays scripted answers and records its argv.

    Answers live in `answers.json` in the returned directory, keyed by the joined argv
    (`{"out": ..., "err": ..., "code": ...}`); `calls.txt` records every invocation. An
    unscripted call exits 3, so a test cannot pass by reaching a command it never named.

    This is the seam a test needs when the defect lives in *which fields a command line
    returns*: replacing the Python function that runs `gh` would replay whatever the test
    author believed `gh` returns, which is exactly how a field `gh` never serves went
    unnoticed. `GH_REPO` is pinned so `github_state.repository()` never asks `gh` for it.
    """
    bin_dir = tmp_path / "scripted-gh"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(f"""#!/usr/bin/env python3
import json, pathlib, sys
here = pathlib.Path({str(bin_dir)!r})
with (here / "calls.txt").open("a") as fh:
    fh.write(" ".join(sys.argv[1:]) + "\\n")
entry = json.loads((here / "answers.json").read_text()).get(" ".join(sys.argv[1:]))
if entry is None:
    sys.stderr.write("no scripted answer\\n")
    raise SystemExit(3)
sys.stdout.write(entry.get("out", ""))
sys.stderr.write(entry.get("err", ""))
raise SystemExit(entry.get("code", 0))
""")
    gh.chmod(0o755)
    (bin_dir / "answers.json").write_text("{}")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("GH_REPO", "o/r")
    return bin_dir


class FakeGh:
    """A `gh` on PATH that replays scripted answers and records what it was asked.

    A real executable rather than a patched `subprocess.run`, because a mock cannot tell you
    the command line is wrong. Answers are keyed by the argv joined with single spaces; each
    may carry `out`, `err` and `code`, and an argv with no answer exits 3 saying so.

    Two records of every invocation, for two kinds of assertion. `calls()` is the joined
    argv, one line each, for reading a command line at a glance. `invocations()` is the argv
    as the list the process received, the directory it ran in, and its standard input --
    what a join cannot show: an argument that itself contains a space, or where it ran.
    Standard input is read only when the answer sets `"read_stdin": true`, so a call that
    pipes nothing cannot leave the fake waiting on the terminal.
    """

    def __init__(self, bin_dir: Path) -> None:
        self.bin_dir = bin_dir
        executable = bin_dir / "gh"
        executable.write_text(f"""#!/usr/bin/env python3
import json, os, pathlib, sys
here = pathlib.Path({str(bin_dir)!r})
argv = sys.argv[1:]
key = " ".join(argv)
entry = json.loads((here / "answers.json").read_text()).get(key)
stdin = sys.stdin.read() if entry is not None and entry.get("read_stdin") else None
with (here / "calls.txt").open("a") as fh:
    fh.write(key + "\\n")
with (here / "invocations.jsonl").open("a") as fh:
    fh.write(json.dumps({{"argv": argv, "cwd": os.getcwd(), "stdin": stdin}}) + "\\n")
if entry is None:
    sys.stderr.write("no scripted answer\\n")
    raise SystemExit(3)
sys.stdout.write(entry.get("out", ""))
sys.stderr.write(entry.get("err", ""))
raise SystemExit(entry.get("code", 0))
""")
        executable.chmod(0o755)
        self.script({})

    def script(self, answers: dict[str, dict[str, Any]]) -> None:
        """Replace every scripted answer."""
        (self.bin_dir / "answers.json").write_text(json.dumps(answers))

    def calls(self) -> list[str]:
        """Each invocation's argv joined by single spaces, in the order they were made."""
        path = self.bin_dir / "calls.txt"
        return path.read_text().splitlines() if path.exists() else []

    def invocations(self) -> list[dict[str, Any]]:
        """Each invocation's exact `argv`, `cwd` and `stdin`, in the order they were made."""
        path = self.bin_dir / "invocations.jsonl"
        lines = path.read_text().splitlines() if path.exists() else []
        return [json.loads(line) for line in lines]

    def forget(self) -> None:
        """Clear both records, keeping the answers, so one test can compare two runs."""
        for name in ("calls.txt", "invocations.jsonl"):
            (self.bin_dir / name).unlink(missing_ok=True)


# Module-level for the same reason as the hook above: pytest resolves fixtures by name. It
# lives here rather than in the one module that first needed it so that every module can
# drive real `gh` command lines through it; a module that defines its own `fake_gh`
# overrides this one for itself.
@pytest.fixture
def fake_gh(tmp_path: Path, monkeypatch) -> FakeGh:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return FakeGh(bin_dir)
