## Title
docs(adr): decision records for 7.a (the searchable ledger) and the forward-compatible reader rule

## Why
Sub-doctrine 12.b and ADR-0020 require a decision record beside every ratified rule, and
`issue-audit/gaps.md` M8 (lines 684-692) found two missing:
- **7.a, the searchable ledger** (`src/vibey_tools/gh/docs/doctrines.md:72-78`): "the ledger
  always has a way for anyone — no matter who — to search it … One standard for every
  searcher: no privileged reader, no gated truth." It is implemented by `vibey ledger search`
  (`src/vibey/cli/ledger_search.py:2`), `vibey ledger export` and `vibey ledger site`
  (`src/vibey/cli/ledger_publication.py:2-14`), the search indexes of
  `migrations/0012_event_search_indexes.sql` and `docs/guides/ledger-publication.md`, and it
  reaches a whole deployment through `vibey ledger search --all-projects`
  (`gap-ledger-search-all-projects-2`). No ADR cites 7.a.
- **The forward-compatible reader rule** (vibey#275 for event kinds, commit `41ff00e1`;
  vibey#287 for every stored vocabulary, commit `56213139`): "readers are forward compatible,
  writers are strict" (`src/vibey/domain/stored_value.py:1-27`). It governs every reader of a
  shared column (`UnrecognizedEventKind`, `src/vibey/domain/ledger.py:77`;
  `EventKindParser`, `:111`; `StoredValueParser`, `stored_value.py:76`), and ADR-0046's
  engine-id aliases extend it. No ADR records it.

## Required behaviour
1. Numbers: the four digits of `ls docs/architecture/decisions | tail -1` are `L`
   (after `gap-docs-adr-records-2`, `0053`). The 7.a record is `NE = L+1`, the reader rule
   `NF = L+2` (`0054`, `0055`).
2. `docs/architecture/decisions/<NE>-the-ledger-is-searchable-by-anyone.md` (about 50-80
   lines, every section present):
   - Line 1: `# <NE> — The ledger is searchable by anyone: one search for every searcher, humans first`
   - Line 3: `**Status:** accepted — sub-doctrine 7.a, which it argues, is ratified · **Date:** <date +%F> · **Cites:** sub-doctrines 7.a, 7.b, 7.c, 10.f · **Related:** ADR-0003, ADR-0032, ADR-0033, ADR-<the 7.c record: ls docs/architecture/decisions/*-the-thorough-ledger.md> · **Evidence:** the tree at the commit this record lands on`
   - `**Owes:**`: the conduct rule is 7.a.
   - `## Context`: the facts in *Why* above.
   - `## Decision`, four numbered points:
     1. Whoever holds a ledger can search it with the same command: `vibey ledger search`
        over a deployment's database, one project or `--all-projects`.
     2. The repository's shard is searchable with no database: `vibey ledger export` writes
        the public, redacted projection, and `vibey ledger site --from FILE --out DIR`
        publishes it as a static, searchable site (`--json-only` for machines).
     3. Output is for humans first and machines second: readable lines by default, JSON on
        request.
     4. No privileged reader: the public projection is one policy for everyone, and what it
        withholds is counted and named, never silently absent
        (`docs/guides/ledger-publication.md`, "How to check what was left out").
   - `## Consequences`: the site generator ships in the distribution, so the presentation
     surface stays available; the search must stay fast as the ledger grows (the indexes of
     migration 0012 and the partitioning of 0013).
   - `## Alternatives rejected`: a hosted log-search product (10.e and 8.b: the family's own
     tool, self-hosted); search only for operators (7.a: no privileged reader); JSON only
     (7.a: humans first).
3. `docs/architecture/decisions/<NF>-stored-values-are-read-forward-compatibly.md`:
   - Line 1: `# <NF> — Stored vocabularies are read forward-compatibly and written strictly`
   - Line 3: `**Status:** accepted — mechanism (ADR-0020), in the tree since vibey#275 and vibey#287; the rules it serves, 7.c and 10.f, are ratified · **Date:** <date +%F> · **Cites:** sub-doctrines 7.c, 10.f · **Related:** ADR-0003, ADR-0016, ADR-0025, ADR-0046 · **Evidence:** commits 41ff00e1 and 56213139; src/vibey/domain/stored_value.py`
   - `**Owes:**`: nothing new as conduct; this records a rule the code already enforces.
   - `## Context`: in a rolling upgrade (KEDA-scaled workers on mixed versions, ADR-0025) or
     after a rollback, an older worker reads rows a newer vibey wrote. Before vibey#275 every
     reader parsed `event.kind` with the closed `EventKind(...)`, so one unknown row raised
     `ValueError` in every older worker; the lease expired and the next older worker died
     the same way (commit `41ff00e1`). vibey#287 found the same for engine ids, phases,
     provenance, job states and circuit states (commit `56213139`).
   - `## Decision`, four numbered points:
     1. A reader parses a stored vocabulary through a `StoredValueParser`: a value it knows is
        its member; anything else is an `Unrecognized…` value carrying the stored text
        verbatim. It never raises and never drops the value.
     2. Consumers match members by identity (`is Phase.BUILD`); anything only a member has
        needs an `isinstance` narrowing first, which the type checker enforces.
     3. Writers take the member type, so vibey only ever writes a value it knows.
     4. Retiring a member never breaks a stored row: its text is read verbatim forever and
        never written again (ADR-0046's rename aliases, for example the stored `opencode`).
   - `## Consequences`: every new closed vocabulary stored in a shared column gets a parser
     and an `Unrecognized…` subclass in the same change; the ledger stays append-only (7.c)
     because no row is ever migrated to a new spelling.
   - `## Alternatives rejected`: rewriting old rows on upgrade (the ledger is append-only, and
     a rolling upgrade has both versions live); raising on an unknown value (one row makes a
     project unreadable to every older worker); dropping it (a silent omission, 7.c).
4. `properdocs.yml`: after the last decision-record entry add
   `- "<NE> — The ledger is searchable by anyone": architecture/decisions/<NE>-the-ledger-is-searchable-by-anyone.md`
   and `- "<NF> — Stored vocabularies are read forward-compatibly": architecture/decisions/<NF>-stored-values-are-read-forward-compatibly.md`,
   in the same form and indentation as the entry above them.
5. The advertised count in the five files becomes the number of files on disk (and the
   `0001–<last>` range in `GEMINI.md`).

## Where to change
- New: the two ADR files. Edit with edit_file: `properdocs.yml` and the five count lines.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider -n 0 tests/meta` passes.
- [ ] Each new record has `## Context`, `## Decision`, `## Consequences`,
      `## Alternatives rejected` and an `**Owes:**` paragraph.
- [ ] `grep -c "41ff00e1\|56213139" docs/architecture/decisions/<NF>-*.md` ≥ 2.
- [ ] Every command the 7.a record names appears in `uv run vibey ledger --help`.

## Tests to write first (TDD)
None new: the ADR meta-tests hold it.

## Checks the lane must run (all must pass)
    uv run pytest -q -p no:cacheprovider -n 0 tests/meta
    uv run vibey ledger --help
    uv run --with 'properdocs==1.6.7' --with 'properdocs-theme-mkdocs==1.6.7' properdocs build --strict --site-dir "$TMPDIR/vibey-site"

## Out of scope
- Code, the canon, the ledger guide, and every other docs file.

Commit as `docs(adr): decision records for 7.a (the searchable ledger) and the forward-compatible reader rule`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
