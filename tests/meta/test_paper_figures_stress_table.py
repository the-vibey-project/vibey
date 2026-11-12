# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A stress record whose rung table holds a cell with no number names the cell, not a traceback.

`StressTable.load` read each numeric cell with `re.search(...).group(0)`, so a cell such as
`n/a` ended the run in `AttributeError: 'NoneType' object has no attribute 'group'` pointing at
a lambda. `StressRecord` (the same table, read for the summary) already refuses it as a
`ValueError` naming the cell; the figure source now does the same.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "paper_figures.py"
# Run in its own interpreter, as the pin and forecast-caption tests do: paper_figures imports
# its siblings as top-level packages whose names collide with other test-imported packages.
PROBE = (
    "import sys\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "import paper_figures\n"
    "try:\n"
    "    paper_figures.StressTable(Path(sys.argv[2]), None).load()\n"
    "except Exception as error:\n"
    "    print(type(error).__name__ + ': ' + str(error))\n"
)
TABLE = (
    "| Concurrency | Result | Wall | p50 | max | Throughput | Free memory |\n"
    "|---|---|---|---|---|---|---|\n"
    "| 1 | 4/4 | 10 | n/a | 4.0 | 1.0 | 3.0 |\n"
)


def test_a_rung_cell_with_no_number_is_a_value_error_naming_the_cell(tmp_path: Path) -> None:
    record = tmp_path / "stress.md"
    record.write_text(TABLE, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-c", PROBE, str(SCRIPT.parent), str(record)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "ValueError: no number in table cell 'n/a'"
