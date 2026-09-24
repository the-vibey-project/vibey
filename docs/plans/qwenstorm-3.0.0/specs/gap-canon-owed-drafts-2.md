## Title
docs(canon): draft the remaining owed sub-doctrines 7.d, 9.f, 9.g, 9.h, 10.h, 10.i, 12.e and 12.f for the operator's ratification

## Why
Gap N3 (`issue-audit/gaps.md:720-728`) listed five owed rules (lane `gap-canon-owed-drafts`).
Reading every ADR at integration HEAD `4317cff6` finds eight more rules the ADRs themselves say
are owed and not proposed. 12.b (`src/vibey_tools/gh/docs/doctrines.md:435-447`) admits no
exceptions, so this lane drafts them all. Each parent is the one the ADR names:
- `docs/architecture/decisions/0004-no-loss-gate-on-handoff.md:5`: "a handoff that fails the gate
  is a retry, an escalation to the full transcript, or a human gate, never a silent partial
  (nearest parent: doctrine 7)". Drafted as **7.d**.
- `0011-agent-surface-provisioning.md:5`: "agent guidance has one source of truth, materialized
  for every engine and changed for all of them in the same change (nearest parent: doctrine 9)".
  Drafted as **9.f**. `gap-agent-tree-parity` and `gap-sd01-carriage` are its tests.
- `0022-absorbed-packages-keep-their-own-gates.md:26` ("owes a sub-doctrine"). Drafted as **9.g**.
- `0023-four-layers-four-floors.md:26` ("owes a sub-doctrine"). Drafted as **9.h**.
- `0001-orchestrate-do-not-reimplement.md:5`: "vibey drives its runners and never calls a provider
  API for build work (nearest ratified neighbour: 10.e)". Drafted as **10.h**.
- `0027-sovereign-design-provider.md:36`: "never emit a citation the model did not fetch — is
  conduct and may deserve its own sub-doctrine under doctrine 10". Drafted as **10.i**, marked
  optional for the operator.
- `0009-human-gates-are-parked-jobs.md:5`: "human input is a parked job … never a worker waiting
  on a person (nearest parent: doctrine 12)". `0029-integrate-serialized-by-advisory-lock.md:26`
  adds "a worker never blocks on a lock; contention is a Defer … belongs in the sub-doctrine
  ADR-0009 owes". Drafted together as **12.e**.
- `0014-optional-visual-design-and-deployment-opt-in.md:5`: "no cloud authority is exercised and
  nothing leaves the machine without an explicit, durable, re-asked human opt-in recorded in the
  ledger (nearest parent: doctrine 12)". Drafted as **12.f**, scoped to what ADR-0014 governs:
  deployment, and design work sent to an external provider. Wider wording would catch declared
  paid engines and publication pushes, which ADR-0014 does not address.
- `0003-event-sourced-ledger.md:5` (append-only) is **not drafted**: 7.c already says "The ledger
  stays append-only: completeness grows by new events, never by rewriting old ones" (`doctrines.md:90-91`).

## Required behaviour
1. After `gap-canon-owed-drafts` has landed, apply these four checked insertions to
   `src/vibey_tools/gh/docs/doctrines.md`: with edit_file, one call per insertion, or by running
   this block from the repository root. No existing line changes.
```python
from pathlib import Path
p = Path("src/vibey_tools/gh/docs/doctrines.md"); s = p.read_text(encoding="utf-8")
E7D = "**7.d — no silent partial handoff** *(ratified by the merge that carried this entry)*: when work passes from one engine to another, nothing the first one knew is lost on the way. The brief that carries it is checked against what the ledger holds before the next engine starts, and a brief that fails the check is never passed on as it stands: it is retried, replaced by the full transcript, or put to a human at a designed moment (Article II.4). A partial handoff that looks complete is the loss this forbids, because the engine that receives it cannot know what it was not told."
E9F = "**9.f — one source of agent guidance** *(ratified by the merge that carried this entry)*: what an agent working on this project is told has one source of truth, and every agent surface — each engine's router file and every tree of skills or rules — carries it, materialized from that source and changed for all of them in the same change. No surface keeps a private variant, and a surface that has drifted from its source is a defect the build reports, not a preference: rotating from one engine to another never changes the rules a project is built under."
E9G = "**9.g — an absorbed package keeps every gate it arrived with** *(ratified by the merge that carried this entry)*: a package the family absorbs into this tree brings its own suite, its own static gates, its own coverage floor and its own oldest supported interpreter, and every one of them runs here on every change from the day of the absorption, so the numbers that were true the day before the import are asserted the day after. Absorption never folds a package's gates into weaker ones, never changes what its floor measures and never drops the oldest interpreter it promised: a floor nothing runs is a claim, not a contract."
E9H = "**9.h — the floor that only rises** *(ratified by the merge that carried this entry)*: every layer of the conductor that carries a coverage floor carries it at every one of its branches, measured and gated separately per layer on every change, so whether the failure path is tested is answered by the build, not by a reviewer's memory. A floor is never lowered to let a change merge: the pressure it puts on a change is relieved by making the tests faster or the change smaller, never by asking less of the tests. A layer outside the floor is an exemption written down with its reason, and an exemption only ever narrows."
E10H = "**10.h — drive the runners, never the provider** *(ratified by the merge that carried this entry)*: vibey orchestrates the family's runners and never reimplements them: build work reaches a model only through a runner the family ships, never through a provider's interface called from the conductor itself. The runner is where a model's limits, credentials, capacity signals and failures are handled once and tested once; a conductor that also spoke to providers directly would hold a second, untested copy of all of it (10.e), and would open a path to the work that a provider could pressure and the family never sees (10.a)."
E10I = "**10.i — no citation without a fetch** *(ratified by the merge that carried this entry)*: no citation, link or quoted source is ever emitted that the system did not itself retrieve and read in the work it cites it for. A model's recollection of a source is a claim, not evidence (10.f): a design, a review or a document names only the sources it fetched, with where and when, and where nothing could be fetched it says so and parks the question for a human instead of inventing a reference."
E12E = "**12.e — a person is never waited on** *(ratified by the merge that carried this entry)*: no worker ever blocks on a human. Work that needs a person's answer becomes a parked job with its question recorded, and the worker moves on to other work; the person answers at a designed moment (Article II.4), in their own time, and the answer returns the work to the queue. Contention between machines is met the same way: a worker never waits on a lock another holds; it defers and comes back. A thread that holds a machine until a person arrives spends the scarcest thing this project has, a person's attention, and wastes the machine besides."
E12F = "**12.f — reach only with a human's yes** *(ratified by the merge that carried this entry)*: no cloud authority is exercised on a project's behalf, and none of its design work is sent to an external provider, without an explicit and durable human opt-in for that project, recorded in the ledger (7.c) and asked again whenever what it would permit changes. Silence, a default, a stale answer or a machine's inference is never consent, and a declined or unanswered opt-in leaves the work complete where it stands, locally."
EDITS = [
    ("never by rewriting old ones.\n\n## 8 — Local authority\n",
     "never by rewriting old ones.\n\n" + E7D + "\n\n## 8 — Local authority\n"),
    ("\n\n## 10 — No guarantees\n",
     "\n\n" + E9F + "\n\n" + E9G + "\n\n" + E9H + "\n\n## 10 — No guarantees\n"),
    ("\n\n## 11 — The living roadmap\n",
     "\n\n" + E10H + "\n\n" + E10I + "\n\n## 11 — The living roadmap\n"),
    ("\n\n---\n\n*The counts are sealed",
     "\n\n" + E12E + "\n\n" + E12F + "\n\n---\n\n*The counts are sealed"),
]
for old, new in EDITS:
    assert s.count(old) == 1, (s.count(old), old[:60])
    s = s.replace(old, new)
p.write_text(s, encoding="utf-8")
```
   The new entries land after 7.c, 9.e, 10.g and 12.d.
2. Regenerate the index: `uv run vibey-gh corpus-index`.
3. The commit body names each entry's source ADR line and parent. It says:
   - 10.i is drafted from a "may deserve" and is the operator's to strike;
   - 12.f is scoped to ADR-0014's reach;
   - ADR-0003 is subsumed by 7.c;
   - the parent and the wording of each entry are the operator's to choose (ADR-0020
     `docs/architecture/decisions/0020-governing-rules-are-ratified-subdoctrines.md:77-78`);
   - ratification triggers Article V.4 at the next release (`constitution.md:140-148`).

## Where to change
- `src/vibey_tools/gh/docs/doctrines.md` (four insertions, eight entries) and
  `src/vibey_tools/gh/corpus-index.json` (regenerated). Nothing else.

## Acceptance criteria
- [ ] `git diff --numstat` shows `doctrines.md` with 16 added and 0 deleted lines.
- [ ] `grep -c "^\*\*7.d — \|^\*\*9.[fgh] — \|^\*\*10.[hi] — \|^\*\*12.[ef] — " src/vibey_tools/gh/docs/doctrines.md` prints 8.
- [ ] `uv run vibey-gh corpus-index --check` exits 0 and `tests/meta/test_corpus_index_is_current.py` passes.

## Tests to write first (TDD)
None new: the corpus meta-test (`gap-canon-rulings-amendment`) fails after step 1 and passes after step 2.

## Checks the lane must run (all must pass)
    uv run vibey-gh corpus-index --check
    uv run pytest -q -p no:cacheprovider tests/meta
    cd src/vibey_tools/gh && python -m pytest -q test/test_corpus.py
    git diff --numstat

## Out of scope
- CLAUDE.md's non-negotiables that no ADR marks as owed ("Credits ≠ rate limit", "a capacity
  rejection always outranks a completion claim", "every job is idempotent under replay"): whether
  they are conduct or mechanism is the operator's call. They are listed in the lane report.
- ADR status notes (docs wave, `gap-docs-*`); CLAUDE.md, AGENTS.md, GEMINI.md, docs/, CHANGELOG.md.

Commit as `docs(canon): draft sub-doctrines 7.d, 9.f–9.h, 10.h, 10.i, 12.e and 12.f (for ratification)`,
with the body in behaviour 3. Do not push.

## Lane card
- **Depends on:** `gap-canon-owed-drafts` (same two files; the letters follow its entries).
- **Kind:** a docs (canon) lane.
- **Ratified by:** the operator's merge only (Article II.3).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
