## Title
docs(canon): draft the owed sub-doctrines 8.i, 9.e, 10.g and 12.d for the operator's ratification

## Why
12.b (`src/vibey_tools/gh/docs/doctrines.md:435-447` at integration HEAD `4317cff6`) and ADR-0020
(`docs/architecture/decisions/0020-governing-rules-are-ratified-subdoctrines.md:35-78`): a rule
that binds future decisions, survives a rewrite and is about conduct is a ratified sub-doctrine,
or it is not a rule. "A machine may draft, a human ratifies" (Constitution Article II.3,
`constitution.md:75-77`). Gap N3 (`issue-audit/gaps.md:720-728`) lists the rules owed and not drafted:
- **ADR-0024:28**: "No unbounded autonomous loop, and no terminal failure a human cannot widen".
  Drafted as **12.d**, under humans first. ADR-0024 says the rule concerns "how the project
  treats people and money", and Article III.2 says "budgets bound every loop".
- **ADR-0025:33**: "a second entry point never grows its own copy of the logic". Drafted as
  **9.e**, under the vibe, beside 9.b's declared seam.
- **ADR-0046 §1** (`specs/ADR-two-loops.md:104-116`): "Sovereignty follows the model and the tool"
  and "a runner the family adds joins one of the two loops as an adapter. It is never a third
  loop". Drafted as one entry, **8.i**, under local authority. It is a new entry, so 8.b's and
  8.c's text is not edited twice (`gap-canon-rulings-amendment` edits them).
- **The #275/#287 reader rule**: "readers are forward compatible, writers are strict"
  (`src/vibey/domain/stored_value.py:10-24`, with no ADR, flagged at `specs/ADR-two-loops.md:370-382`).
  Drafted as **10.g**, under no guarantees: an older or newer peer is never assumed, it is
  confirmed and healed around.
- **ADR-0030:27**: "Paid is opt-in, never a default". **Not drafted.** It is subsumed by 8.b:
  "never, ever, to a paid platform" (`doctrines.md:124-125`); `paidloop` and its adapters "are
  declared-only" (`:131-133`); every hosted equivalent is "declared-only" (`:137`, `:166`).
  8.a also says "Paid platforms are never prioritized" (`:103`). The commit body states this
  finding for the operator, who may reject it and ask for an entry.

Letters follow each doctrine's last entry: 8.h, 9.d, 10.f, 12.c.
The entries are single paragraphs in the established form, as ADR-0020 `:70-72` requires.
The index is rebuilt in the same change (`:75-76`).

## Required behaviour
1. Apply these four checked insertions to `src/vibey_tools/gh/docs/doctrines.md` **after**
   `gap-canon-rulings-amendment` has landed. Use edit_file, one call per insertion (`old` →
   `new`), or run this block as a checked script from the repository root. Each `old` occurs
   exactly once, and no existing line changes.
```python
from pathlib import Path
p = Path("src/vibey_tools/gh/docs/doctrines.md"); s = p.read_text(encoding="utf-8")
E8I = "**8.i — sovereignty follows the model and the tool** *(ratified by the merge that carried this entry)*: an engine is sovereign only when both of its halves are free and run on the operator's own hardware — the model it drives, whose weights anyone may run (8.d), and the tool that drives it, under a free licence, with no account and no subscription. Either half paid makes the whole a paid adapter: the same free tool pointed at a paid provider is a different adapter, in `paidloop`, declared before it runs (8.b), and a tool that is not free is paid-side even when its model is local. A runner the family adds is placed by this rule as an adapter of one of the two loops of 8.c — never a third loop, and never a loop of its own."
E9E = "**9.e — one logic behind every entry point** *(ratified by the merge that carried this entry)*: a second entry point — an operator, an HTTP API, a bot, a scheduler, another command — never grows its own copy of logic an existing entry point already reaches. It calls the one implementation through its declared seam (9.b) and adds only what its own surface needs: parsing its input, presenting its output, and translating its native events into the shared call. Two copies of a rule drift, and the copy nobody tested is the one a user meets; where an entry point cannot reach the shared logic, the logic moves to where every entry point can, and none keeps a private fork of it."
E10G = "**10.g — forward-compatible readers, strict writers** *(ratified by the merge that carried this entry)*: whatever vibey stores may be read back by an older or a newer version of itself — during a rolling upgrade, after a rollback, across a fleet on mixed releases — so every reader of stored data is forward compatible and every writer is strict. A reader that meets a value it has no name for keeps that value's text verbatim, reports it as unrecognized and carries on: it never raises on it, never drops it and never rewrites it, because one unfamiliar row must never make a project unreadable to the rest of the fleet, and the append-only ledger (7.c) keeps every byte it was given. A writer writes only the values its own version knows."
E12D = "**12.d — every bound ends at a human who can widen it** *(ratified by the merge that carried this entry)*: no autonomous loop runs unbounded, and no bound ends in a failure a human cannot widen. Every ladder a machine climbs — retries, repair rounds, escalations, spend — has its bound declared where it is configured (12.c), and reaching the bound parks the work at a designed human moment (Article II.4) that says what was tried, what it cost and exactly what grant would let it continue; a human answers by widening the bound or by closing the work. A machine never widens its own bound, never resets a count to slip past it, and never turns an exhausted bound into a terminal failure that only a code change could reopen."
EDITS = [
    ("can be, never at the expense of these two.\n\n## 9 — The vibe\n",
     "can be, never at the expense of these two.\n\n" + E8I + "\n\n## 9 — The vibe\n"),
    ("\n\n## 10 — No guarantees\n", "\n\n" + E9E + "\n\n## 10 — No guarantees\n"),
    ("\n\n## 11 — The living roadmap\n", "\n\n" + E10G + "\n\n## 11 — The living roadmap\n"),
    ("\n\n---\n\n*The counts are sealed", "\n\n" + E12D + "\n\n---\n\n*The counts are sealed"),
]
for old, new in EDITS:
    assert s.count(old) == 1, (s.count(old), old[:60])
    s = s.replace(old, new)
p.write_text(s, encoding="utf-8")
```
   9.e lands after 9.d and after 9.d's "Terminology — Biodigitology" clarification
   (`doctrines.md:355-364`).
2. Regenerate the index from the repository root: `uv run vibey-gh corpus-index`.
3. The commit body, for the operator:
   - one line per entry, naming its source (`ADR-0024:28`, `ADR-0025:33`, ADR-0046 §1, #275/#287)
     and its parent, and saying that the parent and the wording are the operator's to choose
     (ADR-0020 `:77-78`);
   - the ADR-0030 subsumption finding with the three quoted 8.b clauses;
   - that 8.i joins both ADR-0046 §1 rules in one entry, and can be split in two if preferred;
   - that ratification triggers Article V.4 at the next release (`constitution.md:140-148`).
     Ratifying this lane together with `gap-canon-rulings-amendment` and
     `gap-canon-owed-drafts-2` in one release yanks once.

## Where to change
- `src/vibey_tools/gh/docs/doctrines.md` (four insertions) and `src/vibey_tools/gh/corpus-index.json`
  (regenerated). Nothing else.

## Acceptance criteria
- [ ] `git diff --numstat` shows `doctrines.md` with 8 added and 0 deleted lines.
- [ ] `grep -c "^\*\*8.i — \|^\*\*9.e — \|^\*\*10.g — \|^\*\*12.d — " src/vibey_tools/gh/docs/doctrines.md` prints 4.
- [ ] `uv run vibey-gh corpus-index --check` exits 0.
- [ ] `tests/meta/test_corpus_index_is_current.py` (from `gap-canon-rulings-amendment`) passes.

## Tests to write first (TDD)
None new. The corpus meta-test from `gap-canon-rulings-amendment` is the test: it fails after
step 1 and passes after step 2.

## Checks the lane must run (all must pass)
    uv run vibey-gh corpus-index --check
    uv run pytest -q -p no:cacheprovider tests/meta
    cd src/vibey_tools/gh && python -m pytest -q test/test_corpus.py
    git diff --numstat

## Out of scope
- The rules ADRs owe beyond gap N3's list (`gap-canon-owed-drafts-2`).
- Operator rulings (`gap-canon-rulings-amendment`, `gap-ops-canon-rulings`).
- ADR status notes, which record that a rule is now drafted: the docs wave (`gap-docs-*`).
- CLAUDE.md, AGENTS.md, GEMINI.md, docs/, CHANGELOG.md.

Commit as `docs(canon): draft sub-doctrines 8.i, 9.e, 10.g and 12.d (for ratification)`, with the
body in behaviour 3. Do not push.

## Lane card
- **Depends on:** `gap-canon-rulings-amendment` (same two files; its corpus meta-test).
- **Kind:** a docs (canon) lane.
- **Ratified by:** the operator's merge only (Article II.3).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
