# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every copy of the `vibey loops --json` golden is the golden, byte for byte.

`@vibey/core` parses its own copy of `tests/cli/golden/vibey-loops.json`, and its vitest suite
compares the two, but that suite runs only in the `vibey-core` CI job. A change that regenerates
the golden without the copy then passes every Python gate and leaves the TypeScript client
reading a document vibey no longer prints (SP-LOOPS Task 2 did exactly that: the copy kept
codexloop's withdrawn `mcp: true`). This puts the same check in the suite that regenerates it.
"""

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests" / "cli" / "golden" / "vibey-loops.json"
COPIES = (REPO / "packages" / "vibey-core" / "test" / "fixtures" / "vibey-loops.json",)


@pytest.mark.parametrize("copy", COPIES, ids=lambda p: str(p.relative_to(REPO)))
def test_each_copy_of_the_loops_golden_is_the_golden(copy: Path) -> None:
    assert copy.read_bytes() == GOLDEN.read_bytes(), (
        f"{copy.relative_to(REPO)} drifted from {GOLDEN.relative_to(REPO)}; copy the golden over it"
    )
