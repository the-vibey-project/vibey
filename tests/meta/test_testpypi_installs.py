# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A pre-release install from TestPyPI never resolves dependencies there.

Anyone can upload to TestPyPI. `pip install --pre` with TestPyPI as an index lets a
pre-release of any dependency uploaded there win over PyPI's real one. krypton-app's verify
job did exactly that on 2026-09-30, when a broken `fastapi` build from TestPyPI failed the
install. A `pip install` that names TestPyPI and allows pre-releases must therefore install
`--no-deps`, so only the packages it names come from there.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS = sorted((REPO / ".github" / "workflows").glob("*.yml"))


def pip_installs(text: str) -> list[str]:
    """Every `pip install` command in a workflow, with its continuation lines joined."""
    joined = re.sub(r"\\\n\s*", " ", text)
    return [
        " ".join(line.split())
        for line in joined.splitlines()
        if re.search(r"\bpip install\b", line)
    ]


def test_pip_installs_are_found_across_continuation_lines() -> None:
    text = 'pip install --pre \\\n   --index-url https://test.pypi.org/simple/ \\\n   "x==1"\n'
    assert pip_installs(text) == [
        'pip install --pre --index-url https://test.pypi.org/simple/ "x==1"'
    ]


def test_a_pre_release_install_from_testpypi_takes_no_dependencies_from_it() -> None:
    risky = [
        f"{workflow.name}: {command}"
        for workflow in WORKFLOWS
        for command in pip_installs(workflow.read_text(encoding="utf-8"))
        if "test.pypi.org" in command
        and "--pre" in command.split()
        and "--no-deps" not in command.split()
    ]
    assert not risky, "\n".join(risky)
