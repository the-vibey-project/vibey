# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The research paper passes the mechanical publishability gate on every pull request.

`scripts/paper_publishability.py check` judges `docs/paper.md` and `CITATION.cff` against
the mechanical half of the journal-publishability-criteria skill (the `writing-craft`
plugin of vibey-skills): the contribution statement, the abstract's length, the four
declarations, an AI disclosure that names its tools, no AI author, a citation record that
agrees with the paper, references with a year and a locator, a named evidence cutoff, no
pending markers, no self-promotion, located registrations and complete intervals. Every
threshold and phrase is declared in `scripts/paper_publishability.toml`.

This is the first line: it gates every pull request that updates the paper, so a revision
that drops a declaration or leaves an interval half-stated is red before it merges, and
nobody has to remember to run the script (sub-doctrine 12.e: toil that can be fully
automated is, and the check says out loud when the step was missed). The backstop is
`release-surfaces.yml`, which runs the same command before the paper is rendered and
published, so a paper that reached the release branch by any other route is still checked.

The judgment half -- scope and novelty, methodological soundness, claims the evidence can
carry, null results, reproducibility, text recycling, length -- is printed by the script as
the reviewer's rubric and applied by the review lane, never by this test.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_the_paper_passes_every_required_publishability_check() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/paper_publishability.py", "check"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "docs/paper.md fails the publishability gate; each FAIL row names its line:\n"
        f"{result.stdout}\n{result.stderr}"
    )
