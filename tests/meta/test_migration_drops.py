# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A migration that takes something away from a reader is named where its drain is said.

`migrations/0015_job_bump_named.sql` dropped `job.bump_origin`, which a worker built one
release earlier still read from every `SELECT *` and `RETURNING *`; during a rolling upgrade
that worker fails every job read once the migration commits. The ADR had said the upgrade
was safe under old workers, and the review that caught it came after the merge. Taking a
column or a table away from a running reader is a contract step, safe only once those
readers are gone, so a migration that takes one must be named in an ADR paragraph with a
sentence that names which workers to drain -- a worker, a drain, and the release or
migration that divides old from new, in one sentence. The better shape is
expand-then-contract: stop reading in one release, take it away in a later one.

What counts as taking something away:

- a column dropped, renamed, or retyped (`ALTER TABLE ... DROP [COLUMN] c`,
  `RENAME [COLUMN] c TO d`, `ALTER [COLUMN] c [SET DATA] TYPE t`);
- a table name that existed before the migration and does not after it (`DROP TABLE t`,
  `ALTER TABLE t RENAME TO u` with nothing renamed or created back as `t`). A swap that
  leaves the name in place -- 0013 renames `event` away, builds a partitioned `event`, and
  drops the old copy -- takes nothing away from a reader of `event`.

Dropping a constraint, a default, NOT NULL, an identity or a generation expression takes
no column away, and neither does renaming an index or a constraint.

The SQL is read as PostgreSQL lexes it, so nothing hides from the rule and nothing is
invented by it: `--` and nested `/* */` comments are removed, but only outside strings; a
string literal (`'...'`, `E'...'`) and a dollar-quoted body (`$$...$$`, `$tag$...$tag$`)
are read as SQL in their own right, which is how a `DO` block and an `EXECUTE` string are
seen; a quoted identifier is a name, whatever it spells.

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

_DOLLAR = re.compile(r"\$([A-Za-z_][A-Za-z_0-9]*)?\$")
_WORD = re.compile(r"\w")
_NAME = r"[\w%.]+"
_ALTER_TABLE = re.compile(
    rf"\bALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:ONLY\s+)?({_NAME})\s+(.*)", re.I | re.S
)
_DROP_COLUMN = re.compile(
    r"\bDROP\s+(?:COLUMN\s+)?(?:IF\s+EXISTS\s+)?"
    r"(?!(?:CONSTRAINT|DEFAULT|NOT|IDENTITY|EXPRESSION)\b)[\w%]+",
    re.I,
)
_RENAME_COLUMN = re.compile(r"\bRENAME\s+(?:COLUMN\s+)?(?!(?:TO|CONSTRAINT)\b)[\w%]+\s+TO\b", re.I)
_RENAME_TABLE = re.compile(rf"\bRENAME\s+TO\s+({_NAME})", re.I)
_RETYPE = re.compile(r"\bALTER\s+(?:COLUMN\s+)?[\w%]+\s+(?:SET\s+DATA\s+)?TYPE\b", re.I)
_DROP_TABLE = re.compile(rf"\bDROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?({_NAME}(?:\s*,\s*{_NAME})*)", re.I)
_CREATE_TABLE = re.compile(
    rf"\bCREATE\s+(?:UNLOGGED\s+|TEMP(?:ORARY)?\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?({_NAME})",
    re.I,
)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_RELEASE = re.compile(r"\b(?:\d{4}|v?\d+\.\d+(?:\.\d+)?)\b")


def _quoted(sql: str, start: int, quote: str, escapes: bool) -> tuple[str, int]:
    """The text between `quote` at `start` and its close, doubled quotes undoubled; and
    the index after the close."""
    body: list[str] = []
    i = start + 1
    while i < len(sql):
        if escapes and sql[i] == "\\":
            body.append(sql[i : i + 2])
            i += 2
        elif sql.startswith(quote * 2, i):
            body.append(quote)
            i += 2
        elif sql[i] == quote:
            return "".join(body), i + 1
        else:
            body.append(sql[i])
            i += 1
    return "".join(body), i


def _skip_comment(sql: str, i: int) -> int:
    """The index after the comment at `i`: a `--` line, or a `/* */` block, nested."""
    if sql.startswith("--", i):
        end = sql.find("\n", i)
        return len(sql) if end < 0 else end
    depth, i = 1, i + 2
    while i < len(sql) and depth:
        if sql.startswith("/*", i):
            depth, i = depth + 1, i + 2
        elif sql.startswith("*/", i):
            depth, i = depth - 1, i + 2
        else:
            i += 1
    return i


def _scan(sql: str) -> tuple[str, list[str]]:
    """`sql` with comments removed and each string or dollar-quoted body replaced by a
    placeholder; and those bodies, which are SQL in their own right."""
    out: list[str] = []
    bodies: list[str] = []
    i = 0
    while i < len(sql):
        tag = _DOLLAR.match(sql, i)
        if sql.startswith(("--", "/*"), i):
            i = _skip_comment(sql, i)
            out.append(" ")
        elif sql[i] == "'":
            escapes = i > 0 and sql[i - 1] in "eE" and not (i > 1 and _WORD.match(sql[i - 2]))
            body, i = _quoted(sql, i, "'", escapes)
            bodies.append(body)
            out.append(" 'literal' ")
        elif sql[i] == '"':
            name, i = _quoted(sql, i, '"', escapes=False)
            out.append(" " + (re.sub(r"\W", "_", name) or "_") + " ")
        elif tag and not (i and _WORD.match(sql[i - 1])):
            end = sql.find(tag.group(0), tag.end())
            end = len(sql) if end < 0 else end
            bodies.append(sql[tag.end() : end])
            out.append(" $body$ ")
            i = end + len(tag.group(0))
        else:
            out.append(sql[i])
            i += 1
    return "".join(out), bodies


def _statements(sql: str) -> list[str]:
    """Every statement in `sql`, and in every string and dollar-quoted body inside it."""
    code, bodies = _scan(sql)
    found = [" ".join(s.split()) for s in code.split(";") if s.strip()]
    for body in bodies:
        found += _statements(body)
    return found


def _bare(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower()


def _contract_steps(sql: str) -> list[str]:
    """What `sql` takes away from a reader that was running before it."""
    steps: list[str] = []
    gone: set[str] = set()
    came: set[str] = set()
    for statement in _statements(sql):
        if created := _CREATE_TABLE.search(statement):
            came.add(_bare(created.group(1)))
        if dropped := _DROP_TABLE.search(statement):
            gone.update(_bare(name) for name in re.split(r"\s*,\s*", dropped.group(1)))
        if not (altered := _ALTER_TABLE.search(statement)):
            continue
        table, actions = _bare(altered.group(1)), altered.group(2)
        if renamed := _RENAME_TABLE.search(actions):
            gone.add(table)
            came.add(_bare(renamed.group(1)))
        for rule, what in (
            (_DROP_COLUMN, "drops"),
            (_RENAME_COLUMN, "renames"),
            (_RETYPE, "retypes"),
        ):
            if rule.search(actions):
                steps.append(f"{what} a column of {table}")
    steps += [f"takes table {name} away" for name in sorted(gone - came)]
    return steps


def _names_the_drain(paragraph: str) -> bool:
    """One sentence names a worker, a drain, and the release or migration dividing them."""
    return any(
        re.search(r"\bdrain", s, re.I)
        and re.search(r"\bworkers?\b", s, re.I)
        and _RELEASE.search(s)
        for s in _SENTENCE_END.split(paragraph)
    )


def _paragraphs_naming(stem: str) -> list[str]:
    found = []
    for adr in sorted(ADRS.glob("*.md")):
        for paragraph in re.split(r"\n\s*\n", adr.read_text(encoding="utf-8")):
            if stem in paragraph:
                found.append(paragraph)
    return found


@pytest.mark.parametrize(
    ("sql", "takes"),
    [
        pytest.param("ALTER TABLE job DROP COLUMN bump_origin;", True, id="drop column"),
        pytest.param("alter table job drop column if exists b;", True, id="lowercase if exists"),
        pytest.param("ALTER TABLE job DROP bump_origin;", True, id="no COLUMN keyword"),
        pytest.param('ALTER TABLE job DROP "bump_origin";', True, id="quoted, no COLUMN"),
        pytest.param('ALTER TABLE job DROP COLUMN "bump origin";', True, id="quoted with space"),
        pytest.param("ALTER TABLE ONLY job DROP COLUMN b;", True, id="ONLY"),
        pytest.param("ALTER TABLE IF EXISTS public.job DROP COLUMN b;", True, id="schema"),
        pytest.param("ALTER\n  TABLE\n job\n  DROP\n  COLUMN\n  b\n;", True, id="multi-line"),
        pytest.param("ALTER TABLE job DROP COLUMN constraint_x;", True, id="keyword prefix"),
        pytest.param("ALTER TABLE job ADD COLUMN a int, DROP COLUMN b;", True, id="second action"),
        pytest.param("ALTER TABLE job /* hi */ DROP COLUMN b;", True, id="comment inside"),
        pytest.param("DO $$ BEGIN ALTER TABLE job DROP COLUMN b; END $$;", True, id="DO block"),
        pytest.param(
            "DO $x$ BEGIN ALTER TABLE job DROP COLUMN b; END $x$;", True, id="tagged dollar"
        ),
        pytest.param(
            "DO $$ BEGIN EXECUTE 'ALTER TABLE job DROP COLUMN b'; END $$;", True, id="EXECUTE"
        ),
        pytest.param(
            "DO $$ BEGIN EXECUTE format('ALTER TABLE %I DROP COLUMN %I', t, c); END $$;",
            True,
            id="EXECUTE format",
        ),
        pytest.param(
            "COMMENT ON TABLE job IS 'a -- b'; ALTER TABLE job DROP COLUMN b;",
            True,
            id="-- in a string",
        ),
        pytest.param(
            "COMMENT ON TABLE job IS '/*'; ALTER TABLE job DROP COLUMN b; "
            "COMMENT ON TABLE job IS '*/';",
            True,
            id="/* in a string",
        ),
        pytest.param(
            "COMMENT ON TABLE job IS E'it\\'s -- x'; ALTER TABLE job DROP COLUMN b;",
            True,
            id="E-string escape",
        ),
        pytest.param("ALTER TABLE job RENAME COLUMN b TO c;", True, id="rename column"),
        pytest.param("ALTER TABLE job RENAME b TO c;", True, id="rename, no COLUMN"),
        pytest.param("ALTER TABLE job ALTER COLUMN priority TYPE text;", True, id="retype"),
        pytest.param(
            "ALTER TABLE job ALTER priority SET DATA TYPE text;", True, id="set data type"
        ),
        pytest.param("ALTER TABLE job RENAME TO jobs;", True, id="rename table"),
        pytest.param("DROP TABLE job_dependency;", True, id="drop table"),
        pytest.param("DROP TABLE IF EXISTS a, b;", True, id="drop tables"),
        pytest.param("-- ALTER TABLE job DROP COLUMN b;\nSELECT 1;", False, id="line comment"),
        pytest.param("/* ALTER TABLE job DROP COLUMN b; */ SELECT 1;", False, id="block comment"),
        pytest.param(
            "/* a /* b */ ALTER TABLE job DROP COLUMN c; */ SELECT 1;", False, id="nested comment"
        ),
        pytest.param("ALTER TABLE job DROP CONSTRAINT IF EXISTS c;", False, id="drop constraint"),
        pytest.param("ALTER TABLE job ALTER COLUMN a DROP DEFAULT;", False, id="drop default"),
        pytest.param("ALTER TABLE job ALTER COLUMN a DROP NOT NULL;", False, id="drop not null"),
        pytest.param(
            "ALTER TABLE job ALTER COLUMN a DROP IDENTITY IF EXISTS;", False, id="drop identity"
        ),
        pytest.param("ALTER TABLE job RENAME CONSTRAINT a TO b;", False, id="rename constraint"),
        pytest.param("ALTER TABLE job ADD COLUMN type text;", False, id="column named type"),
        pytest.param("DROP INDEX IF EXISTS job_claim_idx;", False, id="drop index"),
        pytest.param("ALTER INDEX a RENAME TO b;", False, id="rename index"),
        pytest.param("CREATE TABLE t (id int); DROP TABLE t;", False, id="own table dropped"),
        pytest.param(
            "ALTER TABLE event RENAME TO event_old; CREATE TABLE event_new (id int); "
            "ALTER TABLE event_new RENAME TO event; DROP TABLE event_old;",
            False,
            id="0013-shaped swap",
        ),
    ],
)
def test_the_rule_sees_exactly_what_takes_something_away(sql: str, takes: bool) -> None:
    assert bool(_contract_steps(sql)) is takes, _contract_steps(sql)


@pytest.mark.parametrize(
    ("paragraph", "names"),
    [
        pytest.param(
            "0015 drops it. Every worker from a build before 0015 must be drained first.",
            True,
            id="names the workers",
        ),
        pytest.param("Workers on 3.1 are drained before this runs.", True, id="by version"),
        pytest.param("0015 drops it; drain first.", False, id="the word only"),
        pytest.param("0015 drops it. Drain the workers.", False, id="no release"),
        pytest.param("0015 drops it. Build 0014 must be drained.", False, id="no worker"),
        pytest.param(
            "Workers before 0015 exist. They must be drained.", False, id="split sentences"
        ),
    ],
)
def test_a_drain_is_named_only_by_a_sentence_saying_whose(paragraph: str, names: bool) -> None:
    assert _names_the_drain(paragraph) is names


def test_every_migration_that_takes_something_away_says_whose_drain_it_needs() -> None:
    unexplained = {
        path.name: steps
        for path in sorted(MIGRATIONS.glob("*.sql"))
        if (steps := _contract_steps(path.read_text(encoding="utf-8")))
        and not any(_names_the_drain(p) for p in _paragraphs_naming(path.stem))
    }
    assert not unexplained, (
        "each of these migrations takes something away from a running reader, and no ADR "
        "paragraph names it with a sentence saying which workers to drain before it runs "
        f"(expand, then contract): {unexplained}"
    )


def test_the_rule_has_something_to_hold() -> None:
    # A rename of the migrations directory would leave the rule passing over nothing.
    assert any(_contract_steps(p.read_text(encoding="utf-8")) for p in MIGRATIONS.glob("*.sql"))
