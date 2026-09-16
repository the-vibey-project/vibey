# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Shared fixtures, and the one gate on tests that leave the machine.

The suite must behave the same on a laptop and inside GitHub Actions. Actions exports a
number of variables that the code under test reads, and a test that silently changes
behaviour because of one of them is worse than a failing test: it hides a branch and,
in this case, writes into the real job summary.
"""

from __future__ import annotations

import os

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
