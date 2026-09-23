# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Verification that the visual atlas in docs/paper.md is reproducible and in sync with tracked sources."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PAPER = REPO / "docs" / "paper.md"


def test_paper_figures_check_passes_without_drift() -> None:
    """scripts/paper_figures.py --check exits 0: in a full clone every one of the 15 empirical
    figures matches its sources; a shallow clone checks the ten it can and names the rest."""
    result = subprocess.run(
        [sys.executable, "scripts/paper_figures.py", "--check", "--paper", str(PAPER)],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Figure drift detected in docs/paper.md:\n{result.stderr}\n{result.stdout}"
    )


def test_all_empirical_figures_present_in_paper() -> None:
    """Every one of the 15 empirical figure marker pairs is present in docs/paper.md."""
    text = PAPER.read_text(encoding="utf-8")
    expected_figures = [
        "stress-dashboard",
        "stress-cumulative",
        "qwen-runs",
        "storm-lanes",
        "storm-timeline",
        "bench-hosts",
        "host-context",
        "commits-daily",
        "commit-rhythm",
        "cumulative-commits",
        "release-cadence",
        "codebase-shape",
        "forecast",
        "governance-time",
        "completion-band",
    ]
    for name in expected_figures:
        begin_marker = f"<!-- BEGIN GENERATED figure:{name}"
        end_marker = f"<!-- END GENERATED figure:{name} -->"
        assert begin_marker in text, f"Missing begin marker for figure:{name} in docs/paper.md"
        assert end_marker in text, f"Missing end marker for figure:{name} in docs/paper.md"


def test_every_figure_of_the_atlas_is_present_and_numbered_in_order() -> None:
    """The paper's visual atlas: twenty drawn figures and fifteen computed ones, in the
    order the PDF numbers them, with every `[Fig. N]` reference carrying that number."""
    text = PAPER.read_text(encoding="utf-8")
    expected_labels = (
        "fig:family-tree",
        "fig:layer-map",
        "fig:ledger-handoff",
        "fig:six-phase-machine",
        "fig:cdd-orbits",
        "fig:cdd-loop",
        "fig:digital-atom",
        "fig:software-molecule",
        "fig:digital-hierarchy",
        "fig:web-ecology",
        "fig:qwen-cdd",
        "fig:capacity-taxonomy",
        "fig:engine-pool",
        "fig:evaluation-automaton",
        "fig:exact-head",
        "fig:trust-separation",
        "fig:record-effect",
        "fig:stress-rate",
        "fig:stress-cumulative",
        "fig:qwen-runs",
        "fig:qwen-disposition",
        "fig:evidence-watermark",
        "fig:storm-lanes",
        "fig:storm-timeline",
        "fig:bench-hosts",
        "fig:host-context",
        "fig:commits-daily",
        "fig:commit-rhythm",
        "fig:cumulative-commits",
        "fig:release-cadence",
        "fig:codebase-shape",
        "fig:six-materials",
        "fig:completion-band",
        "fig:forecast",
        "fig:governance-time",
    )
    positions = [text.index(rf"\label{{{label}}}") for label in expected_labels]
    assert positions == sorted(positions), "the figures are not in the order the paper lists them"
    assert text.count(r"\begin{figure") == len(expected_labels)
    references = re.findall(r"\[Fig\. (\d+)\]\(#(fig:[a-z-]+)\)", text)
    assert references, "the prose never references a figure"
    for number, label in references:
        assert int(number) == expected_labels.index(label) + 1, f"[Fig. {number}] points at {label}"


def test_every_section_closes_in_plain_words() -> None:
    """Doctrine 7, the never-lost reader: the formal text is restated for a non-specialist."""
    text = PAPER.read_text(encoding="utf-8")
    assert text.count(r"\begin{plainwords}[The paper in plain words]") == 1
    assert text.count(r"\begin{plainwords}") >= 12
