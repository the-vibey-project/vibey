# 0052 — A tracker is kept true by the machinery that changes what it describes, and failure is recorded as failure

**Status:** proposed · **Date:** 2026-09-23 · **Cites:** sub-doctrine 12.i which this record implements, and 12.e, 10.f, 12.d · **Related:** ADR-0047, ADR-0040 · **Evidence:** the QwenStorm ledgers on 2026-09-23 — `integrated.txt` and `abandoned.txt` with six readers and no writer, 4 merged lanes recorded nowhere, 13 dead lanes recorded nowhere, and 190 of 594 queued lanes silently ineligible as a result

**Owes:** nothing new as conduct — 12.i is the conduct and is ratified separately (ADR-0020:
the record argues, the canon states). It owes the advertised ADR count in `CLAUDE.md`,
`AGENTS.md`, `GEMINI.md`, `README.md` and `docs/index.md`
(`tests/meta/test_adr_counts.py`), and a nav entry in `properdocs.yml`.

## Context

The operator's instruction was that the issue list must be up to date at all times, forever.

The storm keeps two ledgers, `integrated.txt` and `abandoned.txt`, and they decide everything:
`storm-queue.sh` starts a lane only when every dependency is in `integrated.txt`, and reports a
lane blocked only when a dependency is in `abandoned.txt`. Six tools read them.

Nothing could write them. `file-suite.py` said so in a comment — "until a human does the
operator lane and appends its slug there by hand" — and that was the whole write side of the
system. Measured on 2026-09-23, over 31 lanes and a 594-lane queue:

- **4 lanes had merged pull requests** (#1044, #1053, #1054, #1055) and none was in
  `integrated.txt`. Their work was in `develop` and every lane depending on them was still
  waiting, because eligibility is decided by the ledger and the ledger had never heard of them.
- **13 lanes carried the runner's own verdict of `completed: false`** and none was in
  `abandoned.txt`. **190 queued lanes — 32% of the queue — depended transitively on one.**
- Those 190 were not reported blocked. `storm-queue.sh` names a lane blocked only when its
  dependency is IN `abandoned.txt`; with the file empty they simply failed the eligibility test
  on every pass and were skipped in silence.

The storm appeared to be working through 594 lanes. A third of them were dark, and nothing
anywhere said so.

The issue list showed the same shape more mildly: three of the four merged lanes had their
issues closed by GitHub's own closing keywords, and the fourth — #1001, whose pull request
#1055 was merged — was still open, because that pull request body happened not to carry one.
Twelve issues the runner had failed three times each were indistinguishable from twelve nobody
had touched.

## Decision

A tracker is a claim about the present and is kept true by the machinery that changes what it
describes, continuously and without anybody remembering to. `lane-reap.py` is the writer the
ledgers never had, and it runs as a step of the ten-minute cycle.

**A record with readers and no writer is not a ledger.** It is a rumour that six tools believe,
and it fails in the direction that hides: every reader gets a confident answer. Whoever adds the
reader owns the writer. This is 12.e's half-automation with a specific and common shape, and it
is worth naming separately because the read side looks finished.

**Truth is not tidiness, and the asymmetry is the point.** Work that landed is marked done: an
open issue for finished work asks somebody to do it twice. Work that was attempted and failed is
marked attempted-and-failed and is NOT closed — closing it converts "we could not do this" into
"this does not need doing", a lie the tracker then tells every reader afterwards. So the reaper
closes the issue of a landed lane and only labels and comments on the issue of a reaped one.

**The evidence outranks the actor's report on itself.** The first draft reaped every
`completed: false` lane and was wrong about one of thirteen: `split-332-1-transport-seams` says
`completed: false`, because the model did give up, and its pull request #1055 is merged, because
a person finished it afterwards. `completed` is the runner's report on its own effort, never a
statement about whether the work reached `develop`. Filing that as an abandonment would have
recorded a success as a failure and, because abandonment cascades, marked 190 dependents blocked
on a dependency that had in fact succeeded. The forge is therefore consulted first and outranks
the runner's note, per 10.f: a claim names its source, and the forge is the better source for
"did this land".

**Settling a ledger is bookkeeping, not authorship**, which is why a machine may do it with
nobody watching (12.d). Both inputs are somebody else's finding — the forge's merge state and
what `qwenlane.py` wrote after exhausting its attempts — and copying a finding into the file
that six tools read is the distinction 12.d draws between adding the import the file next door
already uses and supplying the definition it was meant to find. It is also reversible in the
only way that matters: un-settling a lane is deleting a line.

**Outward-facing writes are a separate flag.** `--reap` writes local ledgers, `--sync-issues`
closes and comments on issues, `--reap-worktrees` removes directories, and none implies another.
They differ in what undoes them: a ledger line is deleted, a worktree is `git worktree add`ed
again, and a closed issue with a comment on it has already been mailed to everyone watching. The
scheduled pass runs with no flags and reports all three.

## Consequences

Four lanes become integrated, twelve become abandoned, **nine queued lanes become eligible to
start**, and 159 become explicitly blocked rather than invisibly skipped. The storm's own report
of what it is doing becomes checkable against what it is doing.

The reaper is also where worktree hygiene now lives: 21 of 33 worktrees were finished work whose
branch had merged, each a full checkout that a person reading `git worktree list` has to
recognise and dismiss again.

## Alternatives considered

**Close the failed issues too.** Tidier, and false. The work still wants doing; it is the
automated attempt that stopped. A closed issue would remove it from every list a person
searches.

**Have `lane-publish.py` write the ledger as it publishes.** It only ever sees lanes it
publishes, so it could never record the four whose work landed by another route, nor the twelve
that never reached it. The writer has to survey, not to observe in passing.

**Let GitHub's closing keywords do it.** They already do most of it, and "most" is the problem:
they covered three of four, and the miss was invisible.

**Wire the issue writes into the ten-minute pass.** Rejected for now. Closing issues and posting
comments reaches everyone watching the repository and cannot be undone by deleting a line, so
the scheduled pass reports that drift and a person decides when it is written.
