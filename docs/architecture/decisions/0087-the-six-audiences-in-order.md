# 0087 — The six audiences, in order: developers, non-profits, universities, governments, freelance clients, industry

**Status:** proposed · **Date:** 2026-10-07 · **Extends:** ADR-0077 (outcome guides; its reader order) · **Cites:** doctrines 2, 7 and 12; sub-doctrines 2.a, 4.a, 7.e, 10.f and 12.b · **Related:** ADR-0033, ADR-0076 · **Evidence:** `develop` at `c5cc3c9cc`, read 2026-10-07 · **Canon:** proposes sub-doctrine 2.c — *the six audiences*, under doctrine 2 (audience channels), carried on its own branch for the operator's ratification

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md`; a `properdocs.yml` nav entry; `docs/llms.txt` regenerated from that
nav; the canon's entry in `src/vibey_tools/gh/docs/doctrines.md` and its regenerated
`corpus-index.json`. All are in the change that carries this record. **Not in it:** the
six demos themselves (see *Consequences*).

## Context

Who the project serves, and in what order, was never written down as law. Measured at
`c5cc3c9cc`:

- **Doctrine 2 orders levels, not audiences.** "Beginner → engineer → scholar, always in
  that order; industry and executive framing an afterthought, essentially absent." That
  fixes how a document climbs; it does not say which kinds of organisation the project is
  for.
- **Sub-doctrine 2.a names exactly one of them.** Governments, with the military arm as
  the primary emphasis. Nothing in the canon, any decision record, or a tracked file names
  non-profits, universities, freelance clients or open-source developers as audiences
  (`git grep` for each, 2026-10-07, finds only the governance text and the skill corpora).
- **ADR-0077 fixes a reader order for one surface.** Open-source developers, then
  practitioners, then evaluators, for the outcome guides. It orders the sections of a
  page, and has no place for a small mission-driven team, a lab or a client.
- **The one demo is for one reader.** `docs/guides/greeter-live-demo.md` walks a full run
  for someone already deciding to adopt. No demo answers "what is this for *my* kind of
  work?".

A non-profit is the plainest gap: the team that most needs software that holds a budget
(`docs/guides/outcomes/cap-agent-spending.md`), keeps its data where it chooses
(`docs/guides/outcomes/run-agents-on-your-own-hardware.md`) and leaves a record a funder
can read, and the team least able to buy a vendor's answer, is the one the project has
never said it is for.

## Decision

**The project serves six audiences, in this order, on every surface that addresses an
audience; each has its own demo; the order and the demos are law (2.c), not preference.**

1. **Open-source developers** — who might use the project and then build it. First, as
   ADR-0077 and 7.e already treat them.
2. **Non-profits** — small, mission-driven teams. New in this record, and second.
3. **Universities and academia** — the paper, the book and the citation file are theirs.
4. **Governments, with their militaries** — 2.a stands unchanged: the military arm is the
   primary emphasis and civil agencies inherit every guarantee.
5. **Freelance clients** — fixed-scope work, stated as scope and price rather than as a
   pitch.
6. **Industry** — last, and not absent: doctrine 2's "afterthought" is an ordering, and an
   audience served sixth is still served.

Four rules carry it.

1. **Earlier never yields to later.** When surfaces compete for space or attention — a
   navigation bar, a landing page, a release note — a later audience adds to what an
   earlier one has and never displaces it. Reordering is an amendment of the canon, not an
   edit of a page.
2. **Every audience gets a demo.** A demo is a worked, runnable walk-through of vibey doing
   that audience's own kind of work: the commands that run, the evidence beside each claim
   (10.f), the limits in plain view, written for a reader who has never seen the project
   (7.e). The greeter run is the model for its shape, not for its content.
3. **A demo describes the work, never a person.** No adopter, testimonial, endorsement or
   figure that is not real (4.a, ADR-0077 rule 4). The industry demo describes what is
   built and what is checkable; it does not name an employer or advertise a person.
4. **Where the code does not do it yet, the demo says so.** The non-profit demo, for
   example, may claim the spending cap and the local engines only as far as the guides
   above evidence them, and states what it leaves to the adopter. An audience whose demo
   cannot yet be honest gets the shorter demo, not the larger claim.

## Consequences

**Good.** Every audience is named once, in one place, in an order a contributor can cite.
The non-profit is on the page. A new surface has an answer to "who is this for, first?"
that does not depend on whoever wrote the last one.

**Bad.** Six demos are six more things to keep runnable, and a stale demo turns away
exactly the reader it was written for (7.e). Until they exist, 2.c binds more than the
tree delivers; the *Follow-up* section below records what is owed and in what order.

**Neutral.** The sibling portfolio site already lists six tracks in this same order
(`src/data/tracks.ts` in `~/git/portfolio`). This record makes that order law for this
repository; it neither edits nor depends on the site.

## Follow-up: the six demos

**The six demos do not exist.** At `c5cc3c9cc` no per-audience demo is in the repository,
and this record writes none, so 2.c binds more than the tree delivers today. That gap is
stated here rather than hidden, and closing it is the follow-up: **one pull request per
demo**, in the audience order above, each merged before the next begins so that an earlier
audience is never waiting on a later one.

**The non-profit demo goes first.** It is the audience this record adds, and the only one
with no page of any kind. It has real material already: the spending cap in
[cap-agent-spending](../../guides/outcomes/cap-agent-spending.md) and running agents on
your own hardware in
[run-agents-on-your-own-hardware](../../guides/outcomes/run-agents-on-your-own-hardware.md).
Its shape follows rule 2 and its claims stop where rule 4 says: the cap and the local
engines only as far as those guides evidence them, and what a team must still bring
itself said plainly.

Open-source developers follow, then universities, governments, freelance clients and
industry. Each pull request adds its demo, links it from the README and the documentation
index, adds its navigation entry and regenerates `docs/llms.txt`.

## Alternatives rejected

- **Leave the order in ADR-0077.** It orders readers within a guide, it is an ADR and so
  can be argued away, and it has no non-profit, university, client or industry in it.
- **Fold non-profits into "practitioners and teams".** That is the sentence this record
  exists to stop saying: a category broad enough to include everyone is a category that
  puts no one second.
- **One demo for all audiences.** The same facts six ways drifting six ways, the objection
  ADR-0077 raised to one page per audience; but here the *work* differs, so the demos
  differ, and a shared demo would be the brochure it refuses.
- **Rank industry out.** Doctrine 2 says "essentially absent" for executive framing, not
  for the audience. Industry readers are real readers, and last is an ordering, not a
  removal.

## Rule status

This is conduct that binds future decisions, survives a rewrite and is not mechanism, so
under 12.b it is spelled out as a sub-doctrine and then ratified. It is filed as **2.c**
under doctrine 2, beside the government channel (2.a) and the installable-everywhere rule
(2.b). The record argues it; only `src/vibey_tools/gh/docs/doctrines.md` states it. Until
the operator's merge ratifies it, it is a proposal.
