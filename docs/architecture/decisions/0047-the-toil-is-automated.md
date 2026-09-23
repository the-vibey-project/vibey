# 0047 — Anything that can be fully automated to make a developer's life better is, and the judgement never is

**Status:** proposed · **Date:** 2026-09-22 · **Cites:** sub-doctrines 12.b, 12.c, 12.d, 12.e which this record implements, and 10.f · **Related:** ADR-0018, ADR-0028, ADR-0045, ADR-0046 · **Evidence:** the QwenStorm run of 2026-09-22–23 — `docs/plans/qwenstorm-3.0.0/tools/`, and the pause recorded in `RUN-STATE.md`

**Owes:** nothing new as conduct — 12.e is the conduct and is ratified separately (ADR-0020:
the record argues, the canon states). It owes the advertised ADR count in `CLAUDE.md`,
`AGENTS.md`, `GEMINI.md`, `README.md` and `docs/index.md` (`tests/meta/test_adr_counts.py`),
and a nav entry in `properdocs.yml`.

## Context

Everything-as-code (ADR-0018, 12.c) says that state which *can* be declared in the repository
is declared there. This record is its twin for **work**: effort a human expends repeatedly,
which a machine could expend instead.

The night of 2026-09-22 produced the evidence in an unusually clean form, because the same
operator hit the same class of problem four times in four hours.

**Pausing the storm took four steps in a fixed order.** Quiet the watchdog, read the live
state, SIGTERM three processes queue-first, write and commit a snapshot. Every one of those is
remembering, and the order is load-bearing: stopping the storm before quieting the watch fires
the alarm the watch exists for — at 3am, on the operator's phone, about something the operator
asked for. A monitor that cries during a planned shutdown is a monitor that gets muted, and a
muted monitor is worse than none. Nothing about those four steps needed a decision; they
needed doing, in order, correctly, while tired. That is the shape this record is about, and it
is now `tools/storm-stop.py`.

**Two gates could not pass, and both read as the lane's failure.** `checks_of()` split spec
commands with `str.split()`, so `--include='src/vibey/domain/*'` reached coverage with its
apostrophes attached and matched no file: 378 specs, every one answering "No data to report".
Separately, 33 specs measured coverage over `tests/domain` and then judged the whole layer at
`--fail-under=100`, which reports 78% and always will. Both wasted the scarcest thing in the
system — a human's attention, spent inspecting lanes that were never the problem. Neither was
found by thinking harder. They were found by a script that ran the check and printed what it
actually got.

**And a repair rule written that night deleted every line consisting only of `}`**, on the
false reasoning that Python has no closing brace, touching 2833 files that were fine. What
caught it was not care. It was an all-or-nothing revert gated on the file still importing
afterwards — automation that verified its own effect rather than trusting the author's
confidence.

## Decision

Anything that can be **fully** automated to make a human developer's life easier and better is
fully automated. The bar is not difficulty and not frequency; it is whether a human has to do
it *again*.

Three things bound that, and they are the load-bearing part:

1. **Fully, or else automate the check.** A half-automation that still depends on someone
   remembering the step it did not cover is worse than none, because it looks finished and is
   trusted accordingly — the uncovered step becomes the one nobody watches for. Where a task
   cannot be made whole, what gets automated instead is the check that says out loud when the
   remaining step was missed. `storm-watch.py` exists for exactly this reason: nothing can
   guarantee the storm keeps producing, so the automation is the thing that notices when it
   stops.

2. **The judgement is never automated away.** Removing a human from a decision does not make
   their life easier; it makes them absent from their own work, and a decision taken by a
   machine because that was cheaper than presenting it is a decision nobody made. The test is
   whether a careful person doing this a second time would do it identically. If yes, it is
   toil. If the right answer could reasonably differ, it stays with the human and the
   automation surrounds it — gathering, staging, narrowing — so what reaches them is the
   decision and nothing else. `lane-repair.py` adds the import the file next door already uses
   and refuses to supply the definition that import was meant to find; `lane-resolve.py`
   settles a conflict only where the answer comes from the tree, and aborts where it comes
   from taste.

3. **Automation that reports success it did not observe is a liability wearing its clothes.**
   A step that cannot verify its own effect says so. The first version of the storm watchdog
   announced that the storm had died while `storm-queue.sh` sat there at one hour seventeen
   minutes, because `ps` is refused under the sandbox and an empty process table reads exactly
   like an empty machine (10.f).

## Consequences

The obligation runs forward: noticing that a piece of toil exists is now the same as owing its
automation, and "I will just do it by hand this time" is a decision that needs a reason, not a
default. The cost is real — `storm-stop.py` took longer to write than the pause it replaces
took to perform, and it will keep costing until the third or fourth pause.

That trade is accepted on purpose, because the failure it prevents is not "slow". It is the
4am mistake in a sequence nobody wrote down, and the sequence that was written down but
drifted from what the code does. The second is worse, and it is the one a runbook cannot fix —
which is why the answer here is a program and not a document.

It also sets the boundary with 12.d from the other side. There, an agent acting for an absent
operator may not widen a grant into authorship. Here, it may not leave a person doing work no
person should have to do. Both are the same claim: the human's attention is the scarce thing,
and it is spent on judgement or it is wasted.
