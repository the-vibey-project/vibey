## Title
docs(adr): records whose rules the canon ratified say accepted, and a meta-test ties ADR status to the canon

## Why
ADR-0020 and sub-doctrine 12.b: "an ADR records the decision; the canon records the law".
ADR-0039 to ADR-0044 still say `**Status:** proposed` (line 3 of each), although the canon
(`src/vibey_tools/gh/docs/doctrines.md`) marks everything they argue as ratified: 9.c (`:351`),
10.f (`:419`), 9.d (`:353`), 8.b (`:120`) and 8.c (`:196`) (`issue-audit/gaps.md` M7, lines
671-682). ADR-0045 to ADR-0049, landed by `gap-docs-adr-land`, say `proposed` too. A reader
told "proposed" about ratified law is misinformed (7.b, 10.f), and nothing checks it.

Two records genuinely wait: the operator's open rulings (`STORM/specs/gap-ops-canon-rulings.md`)
item 2 is recorded in ADR-0047's status (the cost of 8.f's cache lane), and items 4 and 12 in
ADR-0046's (retiring the opencodeloop runner under 12.c; the VS Code verification). Docs must
not state an open ruling as decided, so those two stay proposed and say what they wait for.

## Required behaviour
1. **Statuses.** Write this script to `.qwenstorm/adr_status.py` (the lane's scratch
   directory, excluded from git) and run `uv run python .qwenstorm/adr_status.py`:
   ```python
   import re
   from pathlib import Path

   D = Path("docs/architecture/decisions")
   NEW = {
       "0039": "accepted — sub-doctrine 9.c, which it argues, is ratified",
       "0040": "accepted — sub-doctrine 10.f, which it argues, is ratified",
       "0041": "accepted — sub-doctrine 9.d, which it argues, is ratified",
       "0042": "accepted — sub-doctrine 8.b, which it argues, is ratified",
       "0043": "accepted — the surfaces it installs are 8.b's defaults, and 8.b is ratified",
       "0044": "accepted — sub-doctrine 8.c, which it implements, is ratified",
       "0045": "accepted — sub-doctrine 8.e, which it implements, is ratified with the reuse-while-valid clause this record asked for",
       "0046": "proposed — awaits the operator's rulings on retiring the opencodeloop runner under 12.c and on the VS Code verification it owes",
       "0047": "proposed — awaits the operator's ruling on the cost of 8.f's cache lane",
       "0048": "accepted — mechanism for the operator's standard of 2026-09-22; every sub-doctrine it cites is ratified",
       "0049": "accepted — mechanism (ADR-0020); the rules it applies, 9.b and 10.e, are ratified",
   }
   for number, status in NEW.items():
       (path,) = D.glob(f"{number}-*.md")
       lines = path.read_text(encoding="utf-8").split("\n")
       i = next(n for n, line in enumerate(lines) if line.startswith("**Status:**"))
       if re.match(r"\*\*Status:\*\* proposed", lines[i]):
           lines[i] = re.sub(r"^\*\*Status:\*\* proposed", "**Status:** " + status, lines[i])
           path.write_text("\n".join(lines), encoding="utf-8")
           print("set", path.name)
       else:
           print("left", path.name, lines[i][:80])
   for number, old, new in (
       ("0045", "8.e (drafted for ratification)", "8.e"),
       ("0047", "(and 8.f, the operator's decision of 2026-09-22, drafted for ratification; 10.f for the evidence rules)",
        "8.f (ratified by the merge of #392), and 10.f for the evidence rules"),
   ):
       (path,) = D.glob(f"{number}-*.md")
       text = path.read_text(encoding="utf-8")
       if text.count(old) == 1:
           path.write_text(text.replace(old, new), encoding="utf-8")
           print("cites", path.name)
   ```
   Every file must print `set`. A `left` line means another lane already changed that status:
   report it in the verdict, and let the meta-test below decide whether it is right.
2. **The meta-test** `tests/meta/test_adr_status_follows_canon.py` (new). Line 1 is copied
   byte-for-byte from line 1 of `tests/meta/test_adr_counts.py`. Then:
   ```python
   """An ADR's status agrees with the canon it argues (ADR-0020, sub-doctrine 12.b).

   An ADR records a decision; the canon records the law. Once the canon ratifies what a record
   argues, the record is accepted, and one still marked "proposed" misinforms its reader (7.b,
   10.f). Six records sat at "proposed" after their rules were ratified (gap M7). A record that
   still waits names what it waits for, in its status: an unratified rule it cites, or the
   operator's ruling it awaits.

   Module-level test functions rather than a class with an interface beside it (ADR-0016),
   following tests/meta/test_tools_matrix_covers_every_package.py: pytest collects `test_*`
   functions, and the rule is about production code.
   """

   from __future__ import annotations

   import re
   from pathlib import Path

   REPO = Path(__file__).resolve().parents[2]
   DECISIONS = REPO / "docs" / "architecture" / "decisions"
   CANON = REPO / "src" / "vibey_tools" / "gh" / "docs" / "doctrines.md"
   ENTRY = re.compile(r"^\*\*(\d{1,2}\.[a-z]) — [^*]+\*\*\s*\*\(([^)]*)\)", re.MULTILINE)
   STATUS = re.compile(r"\*\*Status:\*\*\s*(.*?)(?: · |\n|$)")
   CITES = re.compile(r"\*\*Cites:\*\*(.*?)(?:·|\n\n)", re.DOTALL)
   SUBDOCTRINE = re.compile(r"(?<![\w.])(\d{1,2}\.[a-h])(?!\w)")
   AWAITS = "awaits the operator's ruling"


   def _canon() -> dict[str, bool]:
       """Every sub-doctrine the canon holds, and whether its entry says it is ratified."""
       text = CANON.read_text(encoding="utf-8")
       return {m.group(1): "ratified" in m.group(2) for m in ENTRY.finditer(text)}


   def _records() -> list[tuple[str, str, list[str]]]:
       """(file name, status value, cited sub-doctrines) for every ADR on disk."""
       records = []
       for path in sorted(DECISIONS.glob("0*.md")):
           text = path.read_text(encoding="utf-8")
           status = STATUS.search(text)
           assert status, f"{path.name} has no **Status:** field"
           cites = CITES.search(text)
           cited = SUBDOCTRINE.findall(cites.group(1)) if cites else []
           records.append((path.name, status.group(1).strip(), cited))
       return records


   def test_the_canon_is_parsed() -> None:
       assert {"7.c", "8.b", "8.c", "9.c", "10.f"} <= set(_canon())


   def test_every_cited_subdoctrine_exists_in_the_canon() -> None:
       canon = _canon()
       unknown = [(name, sd) for name, _, cited in _records() for sd in cited if sd not in canon]
       assert not unknown, f"ADRs cite sub-doctrines the canon does not hold: {unknown}"


   def test_an_accepted_record_cites_only_ratified_rules() -> None:
       canon = _canon()
       wrong = [
           (name, sd)
           for name, status, cited in _records()
           if status.lower().startswith("accepted")
           for sd in cited
           if not canon.get(sd, False)
       ]
       assert not wrong, f"accepted ADRs cite unratified sub-doctrines: {wrong}"


   def test_a_proposed_record_names_what_it_waits_for() -> None:
       canon = _canon()
       stale = [
           name
           for name, status, cited in _records()
           if status.lower().startswith("proposed")
           and AWAITS not in status
           and all(canon.get(sd, False) for sd in cited)
       ]
       assert not stale, (
           f"{stale} say 'proposed' although every sub-doctrine they cite is ratified; "
           f"say accepted, or name what they wait for ({AWAITS!r} …)"
       )
   ```

## Where to change
- The eleven ADR files 0039–0049 (by the script only).
- New: `tests/meta/test_adr_status_follows_canon.py`.

## Acceptance criteria
- [ ] The script prints `set` for all eleven files; `grep -c "^\*\*Status:\*\* proposed" docs/architecture/decisions/*.md`
      is non-zero only for 0046 and 0047.
- [ ] Before step 1, the new meta-test fails `test_a_proposed_record_names_what_it_waits_for`
      (naming 0039–0045, 0048, 0049); after it, all four tests pass.
- [ ] `uv run pytest -q -p no:cacheprovider -n 0 tests/meta` passes.
- [ ] `uv run ruff check tests/meta && uv run ruff format --check tests/meta` pass.

## Tests to write first (TDD)
`tests/meta/test_adr_status_follows_canon.py`, as in behaviour 2:
- `test_the_canon_is_parsed`: the canon parser finds 7.c, 8.b, 8.c, 9.c and 10.f.
- `test_every_cited_subdoctrine_exists_in_the_canon`: no ADR cites a sub-doctrine the canon lacks.
- `test_an_accepted_record_cites_only_ratified_rules`: an accepted ADR cites only ratified rules.
- `test_a_proposed_record_names_what_it_waits_for`: a proposed ADR cites an unratified rule or
  names the operator's ruling it awaits.
Write it first, run it, and see the last test fail on today's statuses.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider -n 0 tests/meta
If the pytest session fails at start because no PostgreSQL is reachable, add `--noconftest`.

## Out of scope
- Any status the operator records for a ruling (they write it in ADR-0046's or ADR-0047's
  status when they rule; the meta-test then holds it to the canon).
- Status notes on other ADRs (`gap-docs-adr-status-1`; ADR-0046's docs lane).
- ADR bodies beyond the two `Cites` clean-ups in step 1.

Commit as `docs(adr): records whose rules the canon ratified say accepted, and a meta-test ties ADR status to the canon`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
