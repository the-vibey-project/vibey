# 0050 — The test harness and every automation are kept fast continuously, and speed is never bought with what a check measures

**Status:** proposed · **Date:** 2026-09-23 · **Cites:** sub-doctrine 12.g which this record implements, and 12.e, 10.f · **Related:** ADR-0020, ADR-0023, ADR-0047 · **Evidence:** the QwenStorm night of 2026-09-22–23 — a root pre-push suite at ~3 minutes run on every push of every branch, a tenant suite at ~3 minutes beside it, and eleven faults found in one night that were checks running quickly and measuring nothing

**Owes:** nothing new as conduct — 12.g is the conduct and is ratified separately (ADR-0020:
the record argues, the canon states). It owes the advertised ADR count in `CLAUDE.md`,
`AGENTS.md`, `GEMINI.md`, `README.md` and `docs/index.md`
(`tests/meta/test_adr_counts.py`), and a nav entry in `properdocs.yml`.

## Context

The operator's instruction was direct: the test harness must always be fully optimised for
performance, at all times, always and forever — and the same of every automation.

The cost being named is real and this repository pays it continuously. The root pre-push
gate runs the whole suite twice — once for `test-suite` and again for `coverage-gates` —
before any push of any branch. The gh tenant's own suite is another three minutes. On the
night of 2026-09-22–23 a single branch was pushed five times while a missing dev extra was
diagnosed; the machine ran the full suite on every one of them.

Waiting is 12.e's toil collected at a different register. Toil is work a human has to do
again; waiting is the same tax without even the dignity of doing something. It is levied on
every person, on every change, for the life of the project, and it compounds invisibly
because no single wait is worth complaining about. The damage that never appears in a timing
is the change nobody made because running the suite was not worth it.

## Decision

The harness and every automation are kept fast, continuously and on purpose. 12.g is the
conduct; this record states why it is shaped as it is, and where it departs from the literal
instruction.

**It is a standing property, not a project.** "At all times, always and forever" is taken
seriously and read as continuity rather than as an event. A harness that has grown slower has
acquired a defect and is repaired like any other. Nothing about this is a milestone that can
be completed and then stop being true.

**Speed is never bought with correctness, coverage, or what a check measures.** This is the
part the literal wording does not carry, and the reason it is written down. Read without a
bound, "fully optimised for performance" licenses exactly the failure this repository spent a
night removing: a check that runs quickly and means nothing.

Eleven faults were found in one night, and every one was a claim true about the text it
examined and wrong about the thing it named. `shlex.split` without `comments=True` handing
pytest `#` as a file path, so it reported "no tests ran" in milliseconds. A coverage row for
`errors.py` reported as the reason a lane failed. A test asserting `"qwenloop" not in output`
that matched the checkout's own filesystem path. A snapshot guard that refused every commit
because the committed blob was read through a helper that strips. **555 of 643 specs — 86% —
carried a check line that never ran at all**, and dropping them made the storm's verdict
faster and worthless.

A gate that got faster by measuring less did not get faster. It became a weaker gate wearing
the old gate's name, and it will be trusted at the old gate's strength. The optimisation looks
like progress in the timing and never announces what it stopped checking, which is why the
bound is written into the rule rather than left to judgement.

**An optimisation is measured before it is believed.** It is a claim about behaviour, so 10.f
applies to it exactly as to any other: named, with its object and its cutoff, against the
thing as it actually runs. Work that was not measured is not an optimisation, whatever else it
was. A rewrite believed to be faster, in a repository that has just found eleven instruments
reporting the wrong thing, is a guess wearing a benchmark's clothes.

## Consequences

Harness time becomes a tracked property rather than an accumulating accident, and a regression
in it is reportable like any other defect.

The bound has teeth in the direction that matters. Proposals of the form "drop the coverage
gate, it is slow" are answered by the rule rather than by argument: the per-layer 100% floors
(ADR-0023) are what the gate measures, and a faster gate that measures less is out of scope
for this doctrine, not an instance of it. The same answer covers narrowing a test run to a
subdirectory, sampling a suite, or skipping a hook — each makes the timing better and the
measurement smaller.

The obvious work this opens is legitimate and unblocked: the root pre-push gate runs the full
suite twice for two hooks that could share one run; `pytest-xdist` is already configured and
its `--maxprocesses` is worth measuring rather than assuming; and a push that changes only
markdown still pays for the whole suite. None of those trade away what is measured.

## Alternatives considered

**Take the instruction literally, with no bound.** Rejected. "Fully optimised for performance"
with nothing further said is satisfiable by deleting checks, and on this repository's own
evidence that is the likeliest way it would be satisfied — eleven times in one night, a check
that was fast and meaningless survived precisely because nothing looked past the timing.

**Set a numeric budget — "the suite must run in under N minutes."** Attractive and rejected as
law: a number is a mechanism, and ADR-0020 keeps mechanism in decision records rather than in
the canon. A budget also ages badly as the suite grows honestly, and the pressure it creates
when it is missed points at deleting tests. A budget may be adopted as a tracked target under
this doctrine; it is not the doctrine.

**Say nothing and treat slowness as ordinary engineering judgement.** This is the status quo
that produced a suite run twice per push. Judgement did not catch it because no single run was
the problem.
