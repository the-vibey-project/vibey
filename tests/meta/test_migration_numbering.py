# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every migration has its own number, and the numbers run without a gap.

The migrator applies `migrations/*.sql` in lexical order and records each by its stem.
Two branches that each add "the next" migration pick the same number, and both land
cleanly on their own: #1095's `0015_job_bump_named.sql` and #1100's ledger guard did
exactly that. Merged together, two 0015s apply in whatever order their slugs sort,
which is not the order either author tested. This fails on whichever lands second.

A gap fails too: it means a branch renumbered to make room for one that has not
landed, and it must wait for that one rather than land out of order.
"""

import re
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MIGRATIONS = REPO / "migrations"
NAME = re.compile(r"(?P<number>\d{4})_[a-z0-9_]+\.sql")


def _files() -> list[Path]:
    return sorted(MIGRATIONS.glob("*.sql"))


def test_every_migration_is_named_number_underscore_slug() -> None:
    """Four zero-padded digits, so lexical order -- the order the migrator applies
    them in -- is numeric order."""
    bad = [p.name for p in _files() if not NAME.fullmatch(p.name)]
    assert not bad, f"not NNNN_slug.sql: {bad}"


def test_no_two_migrations_share_a_number() -> None:
    counts = Counter(p.name[:4] for p in _files())
    shared = {
        number: [p.name for p in _files() if p.name.startswith(number)]
        for number, n in counts.items()
        if n > 1
    }
    assert not shared, f"migration numbers used more than once: {shared}"


def test_the_numbers_run_from_0001_without_a_gap() -> None:
    numbers = sorted(int(p.name[:4]) for p in _files())
    assert numbers == list(range(1, len(numbers) + 1)), (
        f"migration numbers are not 0001..{len(numbers):04d} without a gap: {numbers}"
    )
