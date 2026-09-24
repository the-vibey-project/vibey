# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A migration that drops a column is named in an ADR that says what to drain first.

`migrations/0015_job_bump_named.sql` dropped `job.bump_origin`, which a worker built one
release earlier still read from every `SELECT *` and `RETURNING *`; during a rolling upgrade
that worker fails every job read once the migration commits. The ADR had said the upgrade
was safe under old workers, and the review that caught it came after the merge. A dropped
column is a contract step, and it is only safe when the old readers are gone first, so a
migration that drops one must be named in an ADR paragraph that says what has to be
drained. The better shape is expand-then-contract -- stop reading the column in one
release, drop it in a later one -- and the paragraph is where that is recorded either way.

Only `ALTER TABLE ... DROP [COLUMN]` counts; dropping a constraint, a default, NOT NULL,
an identity or a generation expression removes no column a reader maps. Comments are
ignored, so a migration may explain a drop it does not make.

Module-level test functions rather than a class with an interface beside it (ADR-0016),
for the reason tests/meta/test_tools_matrix_covers_every_package.py gives: pytest collects
`test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
MIGRATIONS = REPO / "migrations"
ADRS = REPO / "docs" / "architecture" / "decisions"

_COMMENT = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)
_ALTER_TABLE = re.compile(r"^\s*ALTER\s+TABLE\b", re.IGNORECASE)
_DROP_COLUMN = re.compile(
    r"\bDROP\s+(?:COLUMN\s+)?(?:IF\s+EXISTS\s+)?"
    r"(?!(?:CONSTRAINT|DEFAULT|NOT|IDENTITY|EXPRESSION)\b)\w+",
    re.IGNORECASE,
)
_DRAIN = re.compile(r"\bdrain", re.IGNORECASE)


def _drops_a_column(sql: str) -> bool:
    statements = _COMMENT.sub(" ", sql).split(";")
    return any(_ALTER_TABLE.match(s) and _DROP_COLUMN.search(s) for s in statements)


def _paragraphs_naming(stem: str) -> list[str]:
    found = []
    for adr in sorted(ADRS.glob("*.md")):
        for paragraph in re.split(r"\n\s*\n", adr.read_text(encoding="utf-8")):
            if stem in paragraph:
                found.append(paragraph)
    return found


@pytest.mark.parametrize(
    ("sql", "drops"),
    [
        ("ALTER TABLE job DROP COLUMN bump_origin;", True),
        ("alter table job drop column if exists bump_origin;", True),
        ("ALTER TABLE job DROP bump_origin;", True),
        ("ALTER TABLE job ADD COLUMN a int, DROP COLUMN b;", True),
        ("-- ALTER TABLE job DROP COLUMN bump_origin;\nSELECT 1;", False),
        ("/* ALTER TABLE job DROP COLUMN b; */ SELECT 1;", False),
        ("ALTER TABLE job DROP CONSTRAINT job_bump_origin_with_seq;", False),
        ("ALTER TABLE job ALTER COLUMN a DROP DEFAULT;", False),
        ("ALTER TABLE job ALTER COLUMN a DROP NOT NULL;", False),
        ("ALTER TABLE job ALTER COLUMN a DROP IDENTITY IF EXISTS;", False),
        ("DROP INDEX IF EXISTS job_claim_idx;", False),
    ],
)
def test_the_detector_sees_only_a_dropped_column(sql: str, drops: bool) -> None:
    assert _drops_a_column(sql) is drops


def test_every_migration_that_drops_a_column_is_named_where_the_drain_is_said() -> None:
    unexplained = [
        path.name
        for path in sorted(MIGRATIONS.glob("*.sql"))
        if _drops_a_column(path.read_text(encoding="utf-8"))
        and not any(_DRAIN.search(p) for p in _paragraphs_naming(path.stem))
    ]
    assert not unexplained, (
        "each of these migrations drops a column, and no ADR paragraph names it and says "
        f"which workers must be drained before it runs (expand, then contract): {unexplained}"
    )


def test_the_rule_has_something_to_hold() -> None:
    # A rename of the migrations directory would leave the rule passing over nothing.
    assert any(_drops_a_column(p.read_text(encoding="utf-8")) for p in MIGRATIONS.glob("*.sql"))
