# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The forecast figure's caption names the step the data shows, whatever record comes next.

Its first form read the jump from `records[-3]` to `records[-2]`. That was true only until
the delivery-estimate job appended a record (#1125): regenerated, it would have said the
remaining work "jumped from 708 to 706 when the storm filed its lanes as issues", which
is false, while `--check` failed on develop for not regenerating it. The step is now found
in the data, and the storm is named only when open issues rose at the same record.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "paper_figures.py"
# Running a script puts its own directory on `sys.path`; importing one by path does not, and
# paper_figures.py imports its siblings (`interfaces`, `paper_evidence`).
if str(SCRIPT.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("paper_figures_under_test", SCRIPT)
assert SPEC and SPEC.loader, f"the figure generator is missing: {SCRIPT}"
paper_figures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(paper_figures)
largest_rise = paper_figures.PaperFigureAtlas._largest_rise


def record(at: str, remaining: float, open_issues: int) -> dict[str, Any]:
    return {"recorded_at": at, "remaining": remaining, "open_issues": open_issues}


SEPTEMBER = [
    record("2026-09-19T18:50:00Z", 0, 0),
    record("2026-09-19T18:51:00Z", 24, 24),
    record("2026-09-21T19:27:00Z", 25, 23),
    record("2026-09-23T00:33:00Z", 708, 706),
    record("2026-09-23T05:59:00Z", 706, 704),
]


def test_the_storms_filing_is_named_with_its_numbers_and_date() -> None:
    text = largest_rise(SEPTEMBER)
    assert "remaining jumped from 25 to 708 on Sep 23" in text
    assert "open issues rose from 23 to 706 when the storm filed its lanes as issues" in text


def test_a_later_record_does_not_move_the_step_the_caption_names() -> None:
    """The regression: the record #1125 appended made the old caption describe 708 -> 706."""
    later = [*SEPTEMBER, record("2026-09-24T17:31:00Z", 709, 705)]
    assert largest_rise(later) == largest_rise(SEPTEMBER)


def test_a_rise_without_new_issues_does_not_blame_the_storm() -> None:
    text = largest_rise(
        [record("2026-09-01T00:00:00Z", 10, 5), record("2026-09-02T00:00:00Z", 40, 5)]
    )
    assert text == "remaining jumped from 10 to 40 on Sep 2"


def test_a_ledger_that_never_rose_says_so() -> None:
    falling = [record("2026-09-01T00:00:00Z", 40, 5), record("2026-09-02T00:00:00Z", 30, 5)]
    assert largest_rise(falling) == "remaining never rose from one record to the next"
    assert largest_rise(falling[:1]) == "remaining never rose from one record to the next"
