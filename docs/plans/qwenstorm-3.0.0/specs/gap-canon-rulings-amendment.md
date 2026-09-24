## Title
docs(canon): 8.b, 8.c and 8.d carry the operator's rulings of 2026-09-22 — Code - OSS, claudeloop-local in paidloop, OpenCode's transitional window, Valkey, the RAM tiers (for ratification)

## Why
The operator ruled on 2026-09-22 (`STORM-CONTEXT.md`, "Operator rulings"):
- the cache is **Valkey**, and 8.b's "Redis" names the protocol;
- sovereignloop's VS Code is **Code - OSS / VSCodium**, and Microsoft's VS Code is the paid one;
- **claudeloop-local is a paidloop adapter, declared-only**, because Claude Code is not FOSS;
- OpenCode is never always-on: it is declared-only and transitional until the VS Code adapter
  passes conformance, then it is retired (ADR-0046 §9, `specs/ADR-two-loops.md:287-296`);
- #383's RAM tiers: GPT-OSS 20B is the default wherever it fits, other models are opt-in
  alternatives except where it does not fit, and within a tier an OSI licence wins a tie.

A ruling that binds future work is law only as a ratified sub-doctrine (CLAUDE.md non-negotiable;
12.b, `src/vibey_tools/gh/docs/doctrines.md:435-447`; ADR-0020). "A machine may draft, a human
ratifies" (Constitution Article II.3, `constitution.md:75-77`). The canon text at integration
HEAD `4317cff6` does not say these things yet:
- `doctrines.md:130` says "**VS Code** when its provider is local";
- `:133-135` repeals OpenCode outright;
- `:164` names **Redis**;
- 8.c's paid adapters (`:200-201`) omit `claudeloop-local` and paid VS Code;
- 8.d (`:236-269`) has no tier rule.
This lane drafts the text. The operator's merge ratifies it. This is gap N4
(`issue-audit/gaps.md:730-741`), items 1–4, plus the tiers.

The open rulings are **not** drafted here: 8.c's heading, the 8.f cache cost, #148 against 10.b,
and the 12.c question on retiring opencodeloop are `gap-ops-canon-rulings` items 1–4. 8.c's
heading line (`:196`) is not touched.

ADR-0020's mechanics (`docs/architecture/decisions/0020-governing-rules-are-ratified-subdoctrines.md:68-78`)
require `vibey-gh corpus-index` to be rebuilt in the same change. Nothing enforces that in CI:
`corpus-index --check` runs nowhere under `.github/workflows/`. This lane adds the one
meta-test that does.

## Required behaviour
1. Apply these seven checked replacements to `src/vibey_tools/gh/docs/doctrines.md`, and no other
   change. Use edit_file, one call per edit, with `old` and `new` exactly as below. Each `old`
   occurs exactly once. The block is also a runnable checked script (EDITING-RULES rule 2):
```python
from pathlib import Path
p = Path("src/vibey_tools/gh/docs/doctrines.md"); s = p.read_text(encoding="utf-8")
EDITS = [
("the merge that carried them)*: every operational surface of vibey defaults to\n",
 "the merge that carried them; its sovereign VS Code named as Code - OSS,\n`claudeloop-local` placed in `paidloop`, OpenCode's transitional window stated, and the\ncache named as Valkey, by the merge that carried them)*: every operational surface of vibey defaults to\n"),
("  era's default model (8.d), and **VS Code** when its provider is local — always\n  on, never needing declaration, for every phase. **`paidloop`** and its adapters — `claudeloop`,\n  `codexloop`, `cursorloop`, `agyloop`, and VS Code on a paid provider — are\n  declared-only. OpenCode is repealed as an engine of either loop; VS Code takes\n  its place in both, and the runner that drove OpenCode is retired once the VS Code\n  adapter carries its work.\n",
 "  era's default model (8.d), and **VS Code's open-source build, Code - OSS as\n  VSCodium ships it,** when its provider is local — always on, never needing\n  declaration, for every phase. **`paidloop`** and its adapters — `claudeloop`,\n  `codexloop`, `cursorloop`, `agyloop`, Microsoft's VS Code on a paid provider, and\n  `claudeloop-local`, which is Claude Code driving a local model and is paid-side\n  because its tool is not free — are declared-only. OpenCode stays repealed: it is\n  never always-on and never in a default pool of either loop. Until the VS Code\n  adapter passes the family's live conformance suite, OpenCode runs only where a\n  project declares it, as a transitional adapter, and the runner that drove it is\n  then retired; VS Code takes its place in both loops.\n"),
("the **cache** to\n  **Redis**, the **bus** to **RabbitMQ**,",
 "the **cache** to\n  **Valkey** (it speaks the Redis protocol), the **bus** to **RabbitMQ**,"),
("set by the merge that carried them)*: the family runs",
 "set by the merge that carried them; its paid adapters completed by the merge that\ncarried them)*: the family runs"),
("**`paidloop`** drives every paid engine, with `claudeloop`, `codexloop`,\n`cursorloop` and `agyloop` as its adapters.",
 "**`paidloop`** drives every paid engine, with `claudeloop` (its default),\n`codexloop`, `cursorloop`, `agyloop`, Microsoft's VS Code on a paid provider and\n`claudeloop-local` as its adapters."),
("entry; its designated default recorded by the merge that carried that paragraph)*:\n",
 "entry; its designated default recorded by the merge that carried that paragraph;\nits tiers set by the merge that carried them)*:\n"),
("each choice, the evidence behind it and the date it was made.\n\n**The designated default, for this era**",
 "each choice, the evidence behind it and the date it was made.\n\n**Tiers.** The catalogue sorts the laptops it supports into memory tiers. In every\ntier the designated default below fits, it is that tier's default, and every other\nmodel the catalogue supports there is an opt-in alternative a human names. A tier the\ndesignated default does not fit has a default of its own, chosen on recorded evidence\nas above; within any tier, where two models are otherwise comparable, the licence\nrule above decides, and an OSI-approved licence wins the tie.\n\n**The designated default, for this era**"),
]
for old, new in EDITS:
    assert s.count(old) == 1, (s.count(old), old[:60])
    s = s.replace(old, new)
p.write_text(s, encoding="utf-8")
```
2. Regenerate the index from the repository root: `uv run vibey-gh corpus-index`. It rewrites
   `src/vibey_tools/gh/corpus-index.json` deterministically. Do not edit the JSON by hand.
3. New `tests/meta/test_corpus_index_is_current.py` (provenance header; module docstring citing
   ADR-0020's mechanics and Article V.4, and giving the reason its test is a module function):
   `test_the_corpus_index_matches_the_canon` calls
   `corpus.check(load_config(REPO))` (`from vibey_gh import corpus`,
   `from vibey_gh.config import load_config`, `REPO = Path(__file__).resolve().parents[2]`).
   It asserts `ok`, with the message
   `f"{message} — rebuild it in the same change: uv run vibey-gh corpus-index (ADR-0020)"`.
4. The commit body carries, for the operator, one line per edit on why it does not weaken a
   protection (Article IV.2, `constitution.md:107-109`):
   - Code - OSS narrows the sovereign list to a free build.
   - claudeloop-local moves a non-free tool out of the sovereign side.
   - Valkey names the freer-licensed server for the same protocol (8.a).
   - The tiers only add structure to 8.d's existing licence rule.
   - **OpenCode's transitional window needs the operator's explicit confirmation.** The
     ratified text repeals OpenCode outright. The draft keeps it out of every default pool,
     but lets a declaring project run it until the VS Code adapter passes conformance, as
     ruled. Retiring it under 12.c is still open (`gap-ops-canon-rulings` item 4).
   The body also says: ratification triggers Article V.4's yank of every prior release at the
   next release (`constitution.md:140-148`; `src/vibey_tools/gh/vibey_gh/yank.py:171-184`).

## Where to change
- `src/vibey_tools/gh/docs/doctrines.md` (seven edits), `src/vibey_tools/gh/corpus-index.json`
  (regenerated), new `tests/meta/test_corpus_index_is_current.py`.

## Acceptance criteria
- [ ] `git diff --stat` touches exactly those three files.
- [ ] `grep -n "Redis" src/vibey_tools/gh/docs/doctrines.md` prints only the "(it speaks the Redis
      protocol)" line; `grep -c "claudeloop-local" …/doctrines.md` is 3.
- [ ] 8.c's heading line is unchanged: `grep -n "^\*\*8.c — every loop runs once, fed by a queue\*\*" …/doctrines.md` matches.
- [ ] `uv run vibey-gh corpus-index --check` exits 0, and the new meta-test passes.
- [ ] By hand (then revert): adding a word to `doctrines.md` fails the new meta-test.

## Tests to write first (TDD)
- `tests/meta/test_corpus_index_is_current.py::test_the_corpus_index_matches_the_canon`: it
  passes before the edits (the index is current at `4317cff6`), fails after step 1, and passes
  after step 2.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run vibey-gh corpus-index --check
    uv run pytest -q -p no:cacheprovider tests/meta
    cd src/vibey_tools/gh && python -m pytest -q test/test_corpus.py test/test_yank.py

## Out of scope
- The open rulings (`gap-ops-canon-rulings`), 8.c's heading, and any sub-doctrine other than 8.b, 8.c and 8.d.
- The owed sub-doctrines (`gap-canon-owed-drafts`, `gap-canon-owed-drafts-2`).
- Implementing the rulings in code, the installer or the chart (their own lanes); ADR status
  notes, CLAUDE.md, AGENTS.md, GEMINI.md, docs/ and CHANGELOG.md (the docs wave, `gap-docs-*`).

Commit as `docs(canon): 8.b, 8.c and 8.d carry the operator's rulings of 2026-09-22 (for ratification)`,
with the body in behaviour 4. Do not push.

## Lane card
- **Depends on:** nothing. `gap-canon-owed-drafts` follows it: both rewrite `corpus-index.json`.
- **Kind:** a docs (canon) lane: `doctrines.md`, its regenerated index, one meta-test.
- **Ratified by:** the operator's merge only (Article II.3). The storm integrating the lane is not ratification.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
