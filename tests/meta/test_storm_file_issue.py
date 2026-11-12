# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`file-issue.py` refuses a spec with no title in words, never with a traceback.

A spec reaches this tool after `lint-specs.py` has checked its sections, but the tool is also
run by hand on a single file. Without a `## Title` line the title lookup returned `None`, and
the next call on it raised `AttributeError: 'NoneType' object has no attribute 'group'` --
a crash that names a line of the tool rather than the thing wrong with the spec.

The tool is addressed by path because `file-issue.py` is not an importable name, and it is run
as a subprocess because it is a script: it does its work at import time.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[2] / "docs/plans/qwenstorm-3.0.0/tools/file-issue.py"


def test_a_spec_without_a_title_is_refused_in_words(tmp_path: Path) -> None:
    spec = tmp_path / "untitled.md"
    spec.write_text("## Required behaviour\n\nDo a thing.\n")

    done = subprocess.run(
        [sys.executable, str(TOOL), str(spec)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert done.returncode != 0
    assert "## Title" in done.stderr
    assert "Traceback" not in done.stderr
