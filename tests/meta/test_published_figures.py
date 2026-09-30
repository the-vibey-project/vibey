# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Figures the public pages quote from a test are the figures that test runs.

The README's first screen and the crash case study both say what the chaos test does --
how many workers, how many jobs, how often a claim is abandoned, how long a lease lasts.
A number repeated by hand drifts (tests/meta/test_adr_counts.py says why), and a first
screen that overstates its own evidence is the claim ADR-0076 promises never to make. So
the constants are read out of the test itself, by parsing it, and every page that quotes
them must say exactly those.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CHAOS = REPO / "tests" / "infrastructure" / "db" / "test_chaos.py"
#: Every page that quotes the chaos test, and which of its figures that page quotes.
QUOTING = {
    "docs/case-studies/how-vibey-survives-a-crashed-agent.md": (
        "workers",
        "jobs",
        "lease",
        "crash",
    ),
    "README.md": ("workers", "jobs", "crash"),
    "docs/index.md": ("workers", "jobs", "crash"),
    "CONTRIBUTING.md": ("workers", "jobs", "crash"),
}


def _constants() -> dict[str, object]:
    tree = ast.parse(CHAOS.read_text(encoding="utf-8"))
    found: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                found[target.id] = node.value.value
            elif isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                call = node.value
                if getattr(call.func, "id", None) == "timedelta" and call.keywords:
                    keyword = call.keywords[0]
                    if isinstance(keyword.value, ast.Constant):
                        found[target.id] = (keyword.arg, keyword.value.value)
    return found


def _phrases() -> dict[str, str]:
    constants = _constants()
    lease = constants["LEASE"]
    assert isinstance(lease, tuple), f"{CHAOS.name} no longer declares LEASE as a timedelta"
    unit, amount = lease
    assert unit == "milliseconds", f"the lease is now given in {unit}; update the phrasing"
    return {
        "workers": f"{constants['WORKER_COUNT']} workers",
        "jobs": f"{constants['JOB_COUNT']} jobs",
        "lease": f"{amount}-millisecond lease",
        "crash": f"probability {constants['CRASH_PROBABILITY']}",
    }


@pytest.mark.parametrize("page", sorted(QUOTING))
def test_the_page_quotes_the_chaos_test_as_it_runs(page: str) -> None:
    text = " ".join((REPO / page).read_text(encoding="utf-8").split())
    phrases = _phrases()
    missing = [phrases[key] for key in QUOTING[page] if phrases[key] not in text]
    assert not missing, f"{page} no longer says {missing}, which is what {CHAOS.name} runs"
