# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A migration that takes something away from a reader is named where its drain is said.

`migrations/0015_job_bump_named.sql` dropped `job.bump_origin`, which a worker built one
release earlier still read from every `SELECT *` and `RETURNING *`; during a rolling upgrade
that worker fails every job read once the migration commits. The ADR had said the upgrade
was safe under old workers, and the review that caught it came after the merge. Taking
something a running reader relies on is a contract step, safe only once those readers are
gone, so a migration that takes one must be named in an ADR paragraph with a sentence that
says which workers to drain (see "The drain sentence" below). The better shape is
expand-then-contract: stop reading in one release, take it away in a later one.

What counts as taking something away:

- a column dropped, renamed, or retyped (`ALTER TABLE ... DROP [COLUMN] c`,
  `RENAME [COLUMN] c TO d`, `ALTER [COLUMN] c [SET DATA] TYPE t`);
- a relation -- table, view, materialized view or sequence -- that existed before the
  migration and is not there after it: dropped, renamed away, or moved by `SET SCHEMA`;
- a relation replaced under the same name by one that lacks a column the old one had. The
  columns are known by replaying every earlier migration in order (`CREATE TABLE`,
  `LIKE`, `PARTITION OF`, `ADD`, `DROP` and `RENAME COLUMN`); a replacement whose columns
  cannot be read -- `CREATE TABLE ... AS SELECT`, or a table whose earlier columns are not
  known -- counts, because nothing shows it keeps them. 0013 renames `event` away and
  builds a partitioned `event` with every column the old one had, so it takes nothing;
- a type dropped or renamed, or an enum value renamed (`ALTER TYPE ... RENAME VALUE`):
  vibey maps `phase` and `state` strictly, so a renamed value fails an older worker's
  read exactly as a dropped column does.

Dropping a constraint, a default, NOT NULL, an identity or a generation expression takes
nothing away, and neither does renaming an index or a constraint, or adding an enum value.

The SQL is read as PostgreSQL lexes it, so nothing hides from the rule: `--` and nested
`/* */` comments are removed, but only outside strings and quoted names; a string literal
(`'...'`, `E'...'`, `U&'...'`) and a dollar-quoted body (`$$...$$`, `$tag$...$tag$`) are
read as SQL in their own right, which is how a `DO` block, a function body and an
`EXECUTE` string are seen; literals joined by `||` are read as one string, and an
expression joined to them (`quote_ident(c)`, a variable) stands in as a name, so
`EXECUTE 'ALTER TABLE job DROP COLUMN ' || quote_ident(c)` is seen; a quoted name
(`"..."`, `U&"..."`) is a name, whatever it spells. Every string is read as SQL, so the
text of a `COMMENT ON ... IS '<sql>'` that quotes a drop counts too: a false positive,
deliberately, in the safe direction.

The drain sentence: one sentence, not negated ("no", "not", "never", "none", "without"
before the drain; "not yet" is not a negation), that names a worker, a drain, and the
migration itself -- its number or stem -- or an `N.N.N` release, after a word saying which
side of it the drained workers are on ("before", "older than", "running", "still on", ...).
A year, an ADR number, or a bare "drain" does not name anyone. "e.g." and "i.e." do not end
a sentence.

Module-level test functions rather than a class with an interface beside it (ADR-0016),
for the reason tests/meta/test_tools_matrix_covers_every_package.py gives: pytest collects
`test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
MIGRATIONS = REPO / "migrations"
ADRS = REPO / "docs" / "architecture" / "decisions"

_DOLLAR = re.compile(r"\$([A-Za-z_][A-Za-z_0-9]*)?\$")
_WORD = re.compile(r"\w")
_UNICODE_PREFIX = re.compile(r"U&(?=['\"])", re.I)
_CONCAT = re.compile(r"\s*\|\|\s*")
_TERM = re.compile(r"[\w.]+")
_NAME = r":?[\w%.]+"
_RELATION = r"(?:TABLE|VIEW|MATERIALIZED\s+VIEW|SEQUENCE)"
_ALTER_TABLE = re.compile(
    rf"\bALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:ONLY\s+)?({_NAME})\s*(.*)", re.I | re.S
)
_ALTER_RELATION = re.compile(
    rf"\bALTER\s+{_RELATION}\s+(?:IF\s+EXISTS\s+)?(?:ONLY\s+)?({_NAME})\s*(.*)",
    re.I | re.S,
)
_DROP_COLUMN = re.compile(
    r"\bDROP\s+(?:COLUMN\s+)?(?:IF\s+EXISTS\s+)?"
    r"(?!(?:CONSTRAINT|DEFAULT|NOT|IDENTITY|EXPRESSION)\b)([\w%]+)",
    re.I,
)
_ADD_COLUMN = re.compile(
    r"\bADD\s+(?:COLUMN\s+)?(?:IF\s+NOT\s+EXISTS\s+)?"
    r"(?!(?:CONSTRAINT|PRIMARY|UNIQUE|CHECK|FOREIGN|EXCLUDE)\b)([\w%]+)",
    re.I,
)
_RENAME_COLUMN = re.compile(r"\bRENAME\s+(?:COLUMN\s+)?(?!(?:TO|CONSTRAINT)\b)[\w%]+\s+TO\b", re.I)
_RENAME_TO = re.compile(rf"\bRENAME\s+TO\s+({_NAME})", re.I)
_SET_SCHEMA = re.compile(r"\bSET\s+SCHEMA\b", re.I)
_RETYPE = re.compile(r"\bALTER\s+(?:COLUMN\s+)?[\w%]+\s+(?:SET\s+DATA\s+)?TYPE\b", re.I)
_DROP_RELATION = re.compile(
    rf"\bDROP\s+{_RELATION}\s+(?:IF\s+EXISTS\s+)?({_NAME}(?:\s*,\s*{_NAME})*)", re.I
)
_CREATE_TABLE = re.compile(
    rf"\bCREATE\s+(?:UNLOGGED\s+|TEMP(?:ORARY)?\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    rf"({_NAME})\s*(.*)",
    re.I | re.S,
)
_CREATE_OTHER = re.compile(
    rf"\bCREATE\s+(?:OR\s+REPLACE\s+)?(?:TEMP(?:ORARY)?\s+)?"
    rf"(?:VIEW|MATERIALIZED\s+VIEW|SEQUENCE)\s+(?:IF\s+NOT\s+EXISTS\s+)?({_NAME})",
    re.I,
)
_CREATE_TYPE = re.compile(rf"\bCREATE\s+TYPE\s+({_NAME})", re.I)
_DROP_TYPE = re.compile(rf"\bDROP\s+TYPE\s+(?:IF\s+EXISTS\s+)?({_NAME}(?:\s*,\s*{_NAME})*)", re.I)
_ALTER_TYPE = re.compile(rf"\bALTER\s+TYPE\s+({_NAME})\s+(.*)", re.I | re.S)
_RENAME_VALUE = re.compile(r"\bRENAME\s+VALUE\b", re.I)
_NOT_A_COLUMN = frozenset({"constraint", "primary", "unique", "check", "foreign", "exclude"})

_ABBREVIATION = re.compile(r"\b(e\.g|i\.e|cf|etc|vs)\.", re.I)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_DRAIN = re.compile(r"\bdrain", re.I)
_WORKER = re.compile(r"\bworkers?\b", re.I)
_NEGATION = re.compile(r"\b(?:no|not|never|none|nothing|without|needn't)\b(?!\s+yet\b)", re.I)
_SIDE = r"(?:before|older\s+than|earlier\s+than|prior\s+to|up\s+to|below|running|still\s+on|on)"
_FILLER = r"(?:(?:a|an|the|any|build|builds|release|releases|version|migration|of|from)\s+){0,3}"
_VERSION = r"v?\d+\.\d+\.\d+"


@dataclass
class _Schema:
    """What earlier migrations left: each relation's columns (None when not known), and
    the types. `known` is False for a migration read on its own, where anything it did
    not create is taken to have been there, with columns nobody knows."""

    relations: dict[str, set[str] | None] = field(default_factory=dict)
    types: set[str] = field(default_factory=set)
    known: bool = True


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


def _literal(sql: str, i: int) -> tuple[str, int] | None:
    """The string literal starting at `i` (plain, `E''` or `U&''`), and the index after
    it; None when no literal starts there."""
    prefix = _UNICODE_PREFIX.match(sql, i)
    if prefix:
        return _quoted(sql, prefix.end(), "'", escapes=False)
    if sql[i : i + 2].lower() == "e'" and not (i and _WORD.match(sql[i - 1])):
        return _quoted(sql, i + 1, "'", escapes=True)
    if sql.startswith("'", i):
        return _quoted(sql, i, "'", escapes=False)
    return None


def _term(sql: str, i: int) -> int | None:
    """The index after a simple expression at `i` -- a name, optionally called with a
    balanced argument list -- or None when none starts there."""
    name = _TERM.match(sql, i)
    if not name:
        return None
    i = name.end()
    if not sql.startswith("(", i):
        return i
    depth = 0
    while i < len(sql):
        literal = _literal(sql, i)
        if literal:
            i = literal[1]
            continue
        depth += {"(": 1, ")": -1}.get(sql[i], 0)
        i += 1
        if not depth:
            return i
    return i


def _chain(sql: str, i: int) -> tuple[str, int]:
    """The string a `||` chain starting with the literal at `i` spells: literals joined,
    and each expression in it standing in as a name. The index after it."""
    first = _literal(sql, i)
    if first is None:
        return "", i + 1
    parts, i = [first[0]], first[1]
    while joined := _CONCAT.match(sql, i):
        piece = _literal(sql, joined.end())
        if piece:
            parts.append(piece[0])
            i = piece[1]
            continue
        end = _term(sql, joined.end())
        if end is None:
            break
        parts.append(" expr_ ")
        i = end
    return "".join(parts), i


def _scan(sql: str) -> tuple[str, list[str]]:
    """`sql` with comments removed and each string or dollar-quoted body replaced by a
    placeholder; and those bodies, which are SQL in their own right."""
    out: list[str] = []
    bodies: list[str] = []
    i = 0
    while i < len(sql):
        tag = _DOLLAR.match(sql, i)
        quoted_name = _UNICODE_PREFIX.match(sql, i) if sql[i] in "uU" else None
        if sql.startswith(("--", "/*"), i):
            i = _skip_comment(sql, i)
            out.append(" ")
        elif quoted_name and sql[quoted_name.end()] == '"':
            name, i = _quoted(sql, quoted_name.end(), '"', escapes=False)
            out.append(" " + (re.sub(r"\W", "_", name) or "_") + " ")
        elif _literal(sql, i) and not (sql[i] in "eE" and i and _WORD.match(sql[i - 1])):
            body, i = _chain(sql, i)
            follows_an_expression = "".join(out).rstrip().endswith("||")
            bodies.append(("expr_ " if follows_an_expression else "") + body)
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


def _names(listed: str) -> list[str]:
    return [_bare(name) for name in re.split(r"\s*,\s*", listed)]


def _top_level_items(text: str) -> list[str] | None:
    """The comma-separated items inside the parenthesised list that `text` opens with."""
    if not text.startswith("("):
        return None
    depth, start, items = 0, 1, []
    for i, ch in enumerate(text):
        depth += {"(": 1, ")": -1}.get(ch, 0)
        if ch == "," and depth == 1:
            items.append(text[start:i])
            start = i + 1
        elif ch == ")" and depth == 0:
            items.append(text[start:i])
            return [item.strip() for item in items if item.strip()]
    return None


def _columns(definition: str, schema: _Schema) -> set[str] | None:
    """The columns a `CREATE TABLE` defines, or None when they cannot be read."""
    of = re.match(rf"PARTITION\s+OF\s+({_NAME})", definition, re.I)
    if of:
        return schema.relations.get(_bare(of.group(1)))
    items = _top_level_items(definition)
    if items is None:
        return None
    columns: set[str] = set()
    for item in items:
        first, *rest = item.split(maxsplit=1)
        if first.lower() == "like":
            copied = schema.relations.get(_bare(rest[0].split()[0])) if rest else None
            if copied is None:
                return None
            columns |= copied
        elif first.lower() not in _NOT_A_COLUMN:
            columns.add(first.lower())
    return columns


def _replay(sql: str, schema: _Schema) -> list[str]:
    """Apply `sql` to `schema`, and say what it takes away from a reader that was running
    before it."""
    steps: list[str] = []
    before = {
        name: (set(cols) if cols is not None else None) for name, cols in schema.relations.items()
    }
    left: set[str] = set()
    created: set[str] = set()
    found: set[str] = set()  # read on its own: acted on before this migration created it
    created_types: set[str] = set()

    def existed(name: str) -> bool:
        return name in before if schema.known else name in found

    def gone(name: str) -> None:
        if name not in created:
            found.add(name)
        schema.relations.pop(name, None)
        left.add(name)

    for statement in _statements(sql):
        if table := _CREATE_TABLE.search(statement):
            name = _bare(table.group(1))
            schema.relations[name] = _columns(table.group(2), schema)
            created.add(name)
        if other := _CREATE_OTHER.search(statement):
            schema.relations[_bare(other.group(1))] = None
            created.add(_bare(other.group(1)))
        if new_type := _CREATE_TYPE.search(statement):
            schema.types.add(_bare(new_type.group(1)))
            created_types.add(_bare(new_type.group(1)))
        if dropped := _DROP_RELATION.search(statement):
            for name in _names(dropped.group(1)):
                gone(name)
        if dropped_types := _DROP_TYPE.search(statement):
            for name in _names(dropped_types.group(1)):
                schema.types.discard(name)
                if name not in created_types:
                    steps.append(f"drops type {name}")
        if altered_type := _ALTER_TYPE.search(statement):
            name, actions = _bare(altered_type.group(1)), altered_type.group(2)
            if _RENAME_VALUE.search(actions):
                steps.append(f"renames a value of type {name}")
            elif renamed := _RENAME_TO.search(actions):
                steps.append(f"renames type {name}")
                schema.types.discard(name)
                schema.types.add(_bare(renamed.group(1)))
        if relation := (_ALTER_TABLE.search(statement) or _ALTER_RELATION.search(statement)):
            name, actions = _bare(relation.group(1)), relation.group(2)
            if renamed := _RENAME_TO.search(actions):
                schema.relations[_bare(renamed.group(1))] = schema.relations.get(name)
                gone(name)
            elif _SET_SCHEMA.search(actions):
                gone(name)
            elif _ALTER_TABLE.search(statement):
                steps += _alter_columns(name, actions, schema)
    for name in sorted(left):
        if not existed(name):
            continue
        if name not in schema.relations:
            steps.append(f"takes relation {name} away")
            continue
        old, new = before.get(name), schema.relations[name]
        if old is None or new is None:
            steps.append(f"replaces {name} with columns it cannot compare")
        elif old - new:
            steps.append(f"replaces {name} without {', '.join(sorted(old - new))}")
    return steps


def _alter_columns(table: str, actions: str, schema: _Schema) -> list[str]:
    """What an `ALTER TABLE`'s column actions take away; its known columns updated."""
    steps: list[str] = []
    columns = schema.relations.get(table)
    for rule, what in (
        (_DROP_COLUMN, "drops"),
        (_RENAME_COLUMN, "renames"),
        (_RETYPE, "retypes"),
    ):
        if rule.search(actions):
            steps.append(f"{what} a column of {table}")
    if columns is not None:
        columns -= {m.group(1).lower() for m in _DROP_COLUMN.finditer(actions)}
        columns |= {m.group(1).lower() for m in _ADD_COLUMN.finditer(actions)}
    return steps


def _contract_steps(sql: str, schema: _Schema | None = None) -> list[str]:
    """What `sql` takes away from a reader running before it -- read on its own, or after
    the migrations that made `schema`."""
    return _replay(sql, schema if schema is not None else _Schema(known=False))


def _names_the_drain(paragraph: str, stem: str) -> bool:
    """One sentence, not negated, names a worker, a drain, and which side of this
    migration -- or of an `N.N.N` release -- the drained workers are on."""
    number = stem.split("_", 1)[0]
    side = re.compile(
        rf"\b{_SIDE}\s+{_FILLER}(?:{re.escape(stem)}|{re.escape(number)}|{_VERSION})\b",
        re.I,
    )
    shielded = _ABBREVIATION.sub(lambda m: m.group(1).replace(".", "_") + "_", paragraph)
    for sentence in _SENTENCE_END.split(shielded):
        drain = _DRAIN.search(sentence)
        if (
            drain
            and _WORKER.search(sentence)
            and side.search(sentence)
            and not _NEGATION.search(sentence[: drain.start()])
        ):
            return True
    return False


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
        pytest.param('ALTER TABLE job DROP COLUMN "a--b";', True, id="-- in a quoted name"),
        pytest.param('ALTER TABLE "j/*x" DROP COLUMN b;', True, id="/* in a quoted name"),
        pytest.param('ALTER TABLE U&"job" DROP COLUMN b;', True, id="U& table"),
        pytest.param('ALTER TABLE job DROP COLUMN U&"bump\\005forigin";', True, id="U& column"),
        pytest.param("ALTER TABLE ONLY job DROP COLUMN b;", True, id="ONLY"),
        pytest.param("ALTER TABLE job * DROP COLUMN b;", True, id="name*"),
        pytest.param("ALTER TABLE :tbl DROP COLUMN b;", True, id="psql variable"),
        pytest.param("ALTER TABLE IF EXISTS public.job DROP COLUMN b;", True, id="schema"),
        pytest.param("ALTER\n  TABLE\n job\n  DROP\n  COLUMN\n  b\n;", True, id="multi-line"),
        pytest.param("ALTER TABLE job DROP COLUMN b", True, id="no final semicolon"),
        pytest.param("ALTER TABLE job DROP COLUMN constraint_x;", True, id="keyword prefix"),
        pytest.param("ALTER TABLE job ADD COLUMN a int, DROP COLUMN b;", True, id="second action"),
        pytest.param("ALTER TABLE job /* hi */ DROP COLUMN b;", True, id="comment inside"),
        pytest.param("/* a /* b */ c */ ALTER TABLE job DROP COLUMN b;", True, id="closed nest"),
        pytest.param("DO $$ BEGIN ALTER TABLE job DROP COLUMN b; END $$;", True, id="DO block"),
        pytest.param(
            "DO $a1$ BEGIN ALTER TABLE job DROP COLUMN b; END $a1$;",
            True,
            id="tag with digits",
        ),
        pytest.param(
            "DO $o$ BEGIN EXECUTE $i$ALTER TABLE job DROP COLUMN b$i$; END $o$;",
            True,
            id="dollar inside dollar",
        ),
        pytest.param(
            "SELECT '$$'; ALTER TABLE job DROP COLUMN b; SELECT '$$';",
            True,
            id="$$ in a string",
        ),
        pytest.param(
            "DO $$ BEGIN EXECUTE 'ALTER TABLE job DROP COLUMN b'; END $$;",
            True,
            id="EXECUTE",
        ),
        pytest.param(
            "DO $$ BEGIN EXECUTE U&'ALTER TABLE job DROP COLUMN b'; END $$;",
            True,
            id="U& string",
        ),
        pytest.param(
            "DO $$ BEGIN EXECUTE format('ALTER TABLE %I DROP COLUMN %I', t, c); END $$;",
            True,
            id="EXECUTE format",
        ),
        pytest.param(
            "DO $$ BEGIN EXECUTE 'ALTER TABLE job ' || 'DROP COLUMN b'; END $$;",
            True,
            id="EXECUTE literal || literal",
        ),
        pytest.param(
            "DO $$ BEGIN EXECUTE 'ALTER TABLE job DROP COLUMN ' || quote_ident('b'); END $$;",
            True,
            id="EXECUTE literal || call",
        ),
        pytest.param(
            "DO $$ BEGIN EXECUTE 'ALTER TABLE ' || t || ' DROP COLUMN b'; END $$;",
            True,
            id="EXECUTE literal || name || literal",
        ),
        pytest.param(
            "CREATE OR REPLACE FUNCTION f() RETURNS void LANGUAGE plpgsql AS "
            "$fn$ BEGIN ALTER TABLE job DROP COLUMN b; END $fn$;",
            True,
            id="function body",
        ),
        pytest.param(
            "CREATE FUNCTION f() RETURNS void LANGUAGE sql AS 'ALTER TABLE job DROP COLUMN b';",
            True,
            id="function body in quotes",
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
        pytest.param("SELECT E'\\''; ALTER TABLE job DROP COLUMN b;", True, id="E escaped quote"),
        pytest.param(
            "SELECT e'x\\'y -- z'; ALTER TABLE job DROP COLUMN b;",
            True,
            id="lowercase e-string",
        ),
        pytest.param("SELECT 'a\\'; ALTER TABLE job DROP COLUMN b;", True, id="plain backslash"),
        pytest.param(
            "COMMENT ON COLUMN job.a IS 'ALTER TABLE job DROP COLUMN b';",
            True,
            id="COMMENT quoting a drop (safe false positive)",
        ),
        pytest.param("ALTER TABLE job RENAME COLUMN b TO c;", True, id="rename column"),
        pytest.param("ALTER TABLE job RENAME b TO c;", True, id="rename, no COLUMN"),
        pytest.param("ALTER TABLE job ALTER COLUMN priority TYPE text;", True, id="retype"),
        pytest.param(
            "ALTER TABLE job ALTER priority SET DATA TYPE text;",
            True,
            id="set data type",
        ),
        pytest.param("ALTER TABLE job RENAME TO jobs;", True, id="rename table"),
        pytest.param("ALTER TABLE job SET SCHEMA archive;", True, id="set schema"),
        pytest.param("ALTER VIEW job_view RENAME TO v;", True, id="rename view"),
        pytest.param("DROP TABLE job_dependency;", True, id="drop table"),
        pytest.param("DROP TABLE IF EXISTS a, b;", True, id="drop tables"),
        pytest.param("DROP VIEW job_view;", True, id="drop view"),
        pytest.param("DROP MATERIALIZED VIEW m;", True, id="drop materialized view"),
        pytest.param("DROP SEQUENCE job_bump_seq;", True, id="drop sequence"),
        pytest.param("DROP TYPE phase CASCADE;", True, id="drop type"),
        pytest.param(
            "ALTER TYPE job_state RENAME VALUE 'ready' TO 'queued';",
            True,
            id="rename enum value",
        ),
        pytest.param("ALTER TYPE phase RENAME TO stage;", True, id="rename type"),
        pytest.param(
            "ALTER TABLE job RENAME TO job_old; CREATE TABLE job (id uuid); DROP TABLE job_old;",
            True,
            id="replaced, earlier columns unknown",
        ),
        pytest.param(
            "ALTER TABLE job RENAME TO job_old; CREATE TABLE job AS SELECT id FROM job_old;",
            True,
            id="replaced by CREATE TABLE AS",
        ),
        pytest.param("-- ALTER TABLE job DROP COLUMN b;\nSELECT 1;", False, id="line comment"),
        pytest.param("/* ALTER TABLE job DROP COLUMN b; */ SELECT 1;", False, id="block comment"),
        pytest.param(
            "/* a /* b */ ALTER TABLE job DROP COLUMN c; */ SELECT 1;",
            False,
            id="nested comment",
        ),
        pytest.param("/* a /* b */ ALTER TABLE job DROP COLUMN b;", False, id="unterminated nest"),
        pytest.param("ALTER TABLE job DROP CONSTRAINT IF EXISTS c;", False, id="drop constraint"),
        pytest.param("ALTER TABLE job ALTER COLUMN a DROP DEFAULT;", False, id="drop default"),
        pytest.param("ALTER TABLE job ALTER COLUMN a DROP NOT NULL;", False, id="drop not null"),
        pytest.param(
            "ALTER TABLE job ALTER COLUMN a DROP IDENTITY IF EXISTS;",
            False,
            id="drop identity",
        ),
        pytest.param("ALTER TABLE job RENAME CONSTRAINT a TO b;", False, id="rename constraint"),
        pytest.param("ALTER TABLE job ADD COLUMN type text;", False, id="column named type"),
        pytest.param("ALTER TYPE phase ADD VALUE 'triage';", False, id="add enum value"),
        pytest.param("DROP INDEX IF EXISTS job_claim_idx;", False, id="drop index"),
        pytest.param("ALTER INDEX a RENAME TO b;", False, id="rename index"),
        pytest.param("CREATE TABLE t (id int); DROP TABLE t;", False, id="own table dropped"),
        pytest.param("CREATE VIEW v AS SELECT 1; DROP VIEW v;", False, id="own view dropped"),
        pytest.param("CREATE TYPE t AS ENUM ('a'); DROP TYPE t;", False, id="own type dropped"),
    ],
)
def test_the_rule_sees_exactly_what_takes_something_away(sql: str, takes: bool) -> None:
    assert bool(_contract_steps(sql)) is takes, _contract_steps(sql)


_EVENT = _Schema(relations={"event": {"id", "seq", "payload"}})


@pytest.mark.parametrize(
    ("sql", "takes"),
    [
        pytest.param(
            "ALTER TABLE event RENAME TO event_old; "
            "CREATE TABLE event_new (id uuid, seq bigint, payload jsonb, CHECK (seq > 0)); "
            "ALTER TABLE event_new RENAME TO event; DROP TABLE event_old;",
            False,
            id="0013-shaped swap keeping every column",
        ),
        pytest.param(
            "ALTER TABLE event RENAME TO event_old; CREATE TABLE event (LIKE event_old); "
            "DROP TABLE event_old;",
            False,
            id="replaced LIKE the old",
        ),
        pytest.param(
            "ALTER TABLE event RENAME TO event_old; CREATE TABLE event (id uuid, seq bigint); "
            "DROP TABLE event_old;",
            True,
            id="replaced without a column",
        ),
        pytest.param(
            "ALTER TABLE event RENAME TO event_old; "
            "CREATE TABLE event AS SELECT id, seq, payload FROM event_old;",
            True,
            id="replaced by CREATE TABLE AS",
        ),
    ],
)
def test_a_replacement_is_measured_against_the_columns_before_it(sql: str, takes: bool) -> None:
    schema = _Schema(relations={k: set(v or ()) for k, v in _EVENT.relations.items()})
    assert bool(_contract_steps(sql, schema)) is takes


@pytest.mark.parametrize(
    ("paragraph", "stem", "names"),
    [
        pytest.param(
            "0015 drops it. Every worker from a build before 0015 must be drained first.",
            "0015_job_bump_named",
            True,
            id="names the workers",
        ),
        pytest.param(
            "Every worker built before 0015 must be drained first.",
            "0015_job_bump_named",
            True,
            id="reviewer: built before",
        ),
        pytest.param(
            "Workers (e.g. those before 0015) must be drained.",
            "0015_job_bump_named",
            True,
            id="reviewer: e.g. is not a sentence end",
        ),
        pytest.param(
            "Every worker not yet running 0015 must be drained.",
            "0015_job_bump_named",
            True,
            id="not yet is not a negation",
        ),
        pytest.param(
            "Workers still on 3.1.0 are drained before this runs.",
            "0017_x",
            True,
            id="by N.N.N release",
        ),
        pytest.param(
            "Workers may need draining at some point in 2026.",
            "0015_job_bump_named",
            False,
            id="reviewer: a year",
        ),
        pytest.param(
            "No worker needs to be drained before 0016.",
            "0016_ledger_append_only_guard",
            False,
            id="reviewer: negated",
        ),
        pytest.param(
            "Draining workers is covered by 1.0 docs.",
            "0015_job_bump_named",
            False,
            id="reviewer: N.N is not a release",
        ),
        pytest.param(
            "The drain of worker pools is handled; see ADR-0044.",
            "0015_job_bump_named",
            False,
            id="reviewer: an ADR number",
        ),
        pytest.param(
            "Worker drain: 0015.",
            "0015_job_bump_named",
            False,
            id="reviewer: no side named",
        ),
        pytest.param(
            "Workers on 3.1 are drained before this runs.",
            "0017_x",
            False,
            id="N.N release",
        ),
        pytest.param("0015 drops it; drain first.", "0015_job_bump_named", False, id="word only"),
        pytest.param(
            "0015 drops it. Drain the workers.",
            "0015_job_bump_named",
            False,
            id="no release",
        ),
        pytest.param(
            "Builds before 0015 must be drained.",
            "0015_job_bump_named",
            False,
            id="no worker",
        ),
        pytest.param(
            "Workers before 0015 exist. They must be drained.",
            "0015_job_bump_named",
            False,
            id="split sentences",
        ),
        pytest.param(
            "Every worker before 0014 must be drained.",
            "0015_job_bump_named",
            False,
            id="another migration",
        ),
    ],
)
def test_a_drain_is_named_only_by_a_sentence_saying_whose(
    paragraph: str, stem: str, names: bool
) -> None:
    assert _names_the_drain(paragraph, stem) is names


def _replayed() -> dict[str, list[str]]:
    """Every migration's contract steps, each read after the ones before it."""
    schema = _Schema()
    return {
        path.name: _contract_steps(path.read_text(encoding="utf-8"), schema)
        for path in sorted(MIGRATIONS.glob("*.sql"))
    }


def test_every_migration_that_takes_something_away_says_whose_drain_it_needs() -> None:
    unexplained = {
        name: steps
        for name, steps in _replayed().items()
        if steps
        and not any(
            _names_the_drain(p, name.removesuffix(".sql"))
            for p in _paragraphs_naming(name.removesuffix(".sql"))
        )
    }
    assert not unexplained, (
        "each of these migrations takes something away from a running reader, and no ADR "
        "paragraph names it with a sentence saying which workers to drain before it runs "
        f"(expand, then contract): {unexplained}"
    )


def test_the_replay_knows_every_table_and_takes_only_what_0015_took() -> None:
    # A replay that lost track of the schema would pass over replacements it cannot read;
    # a rename of the migrations directory would leave the rule passing over nothing.
    assert {name: steps for name, steps in _replayed().items() if steps} == {
        "0015_job_bump_named.sql": ["drops a column of job"]
    }
