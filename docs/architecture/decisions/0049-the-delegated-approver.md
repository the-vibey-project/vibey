# 0049 — A named agent may give the approval an unattended change needs, and is never the author of what it approves

**Status:** proposed · **Date:** 2026-09-23 · **Cites:** sub-doctrine 12.f which this record implements, and 12.b, 12.d, 12.e, 10.f · **Related:** ADR-0020, ADR-0028, ADR-0046, ADR-0047 · **Evidence:** the QwenStorm night of 2026-09-22–23 — `PR review / gate` failing on every pull request with the run's own text "an infrastructure or operator failure rather than a defect in the pull request"; PRs #1053–#1059, which reached 51 green checks each and merged only when the operator merged them by hand at 09:25–09:27Z; the nine Copilot review findings on #1055–#1058, every one of them real

**Owes:** nothing new as conduct — 12.f is the conduct and is ratified separately (ADR-0020:
the record argues, the canon states). It owes the advertised ADR count in `CLAUDE.md`,
`AGENTS.md`, `GEMINI.md`, `README.md` and `docs/index.md`
(`tests/meta/test_adr_counts.py`), and a nav entry in `properdocs.yml`.

## Context

An unattended run can do everything except the last step. On the night of 2026-09-22–23 the
storm produced work, the agent reviewed and repaired it, the deterministic gates ran, and
seven pull requests reached fifty-one passing checks apiece. Not one of them merged. Every
one was held by `PR review / gate`, and the gate was honest about why:

> Scans passed for this exact head, but the exact-head review returned no verdict (review
> job: failure) and no local fallback verdict was produced either. This is an infrastructure
> or operator failure rather than a defect in the pull request.

The merge train was not broken and was not idle: the storm's own cycle ran
`vibey-gh merge-train` nineteen times overnight, exit 0 every time, and correctly declined
every pull request with a stated reason. The work landed at 09:25–09:27Z because the
operator woke and merged seven pull requests by hand — which is the step the whole
arrangement exists to remove.

So the question is not whether the pipeline works. It is whether the last human checkpoint
can be delegated without becoming a rubber stamp.

### The night argues both sides, and both are evidence

**Review by an independent reader caught what the gates could not.** Copilot raised nine
findings across #1055–#1058. All nine were real. The sharpest: adding one name to an import
block silently dropped `ProtectedRefInterface` from it while leaving it in `__all__`, so
`from vibey_gh.interfaces import ProtectedRefInterface` raised `ImportError` for an
interface that still existed. **The tenant's 2512 tests passed at 100% line and branch
coverage**, because no test imported that name from the package — exactly the gap `__all__`
exists to cover, and precisely what nothing was checking. Three more findings were of the
same family: a gate pointed at the wrong environment, a regression test CI never ran, a
failed lookup converted to a benign empty string.

**And review by a reader with context caught what no independent process could.** Seven
faults found that night shared one shape — a claim true about the text and wrong about what
it measured. `shlex.split` without `comments=True` handing pytest `#` as a file path; a
coverage row for `errors.py` reported as the reason a lane failed; a stray `src/__init__.py`
failing `mypy --strict` across all 343 source files while naming a file nobody touched;
`assert "qwenloop" not in res.output` failing against a substring of the checkout's own
filesystem path. Every one of those checks ran, reported, and was counted. None of them
could have been caught by running them again.

Neither reader was sufficient alone. That is the finding, and it decides the shape of the
rule: the value of review is independence from authorship, not the identity of the reviewer.

## Decision

An operator may name an agent to give, while they are away, the approval a change needs
before it lands. The conduct is 12.f; this record states why it takes the shape it does.

**The approver is never the author.** This is the load-bearing constraint and the only one
that cannot be traded. Whatever wrote a change does not approve it, and an agent that
repaired a change authored that repair however little it touched. The question is who wrote
the diff in front of the reviewer, not whose name is on the branch — which matters here
because by the time a lane was publishable that night, the reviewing agent had usually
rewritten a great deal of it. Calling such a branch "the model's work, independently
approved" would be a fiction, and the rule is written to make that fiction unavailable.

**Judgement is not automated away, which 12.e forbids.** 12.e is explicit that "a decision
taken by a machine because that was cheaper than presenting it is a decision nobody made".
Approving a change is judgement; the right answer can reasonably differ. What resolves the
tension is *whose* judgement operates. The operator exercises it once, in the grant, by
fixing the class of change that may be approved and the classes that never may. The agent
applies a standard it did not choose and cannot alter. An agent selecting its own standard
would be the decision nobody made; an agent applying the operator's is the operator still
deciding, at a distance they chose.

**An approval is evidence, not ceremony (10.f).** It names what it checked, names what it
could not check, and withholds itself where the evidence does not reach. An approval that
cannot say what it rests on is worse than none, because it will be believed.

**The mandate cannot widen itself.** The grant, the gates beside it, the governance corpus,
and any rule deciding who may approve are outside what a delegated approver may approve.
This record was written under that constraint: the agent that drafted it declined to edit
the settings file governing its own permissions, and asked the operator to do it.

**Withdrawal is instant, unilateral, and needs no reason.** Granting is deliberate, declared
and reviewed, per 12.c. Withdrawing needs no merge, no quorum and no notice, binds from the
moment it happens, and leaves whatever was in flight for a person. The absence of a grant is
refusal, never permission, so the mechanism fails closed: a delegated approver that cannot
read its own authorization has already lost it. The asymmetry is the protection — the power
to stop must never be harder to exercise than the power that was given.

## Consequences

An unattended run can now finish. The class of change an approver may pass is the operator's
to set and to narrow; nothing here decides it, and nothing here lets the agent decide it.

The deterministic gates keep their standing. A delegated approval is added to them and never
substituted for one, so every failure mode the gates already catch is caught exactly as
before — which matters, because the gates were the thing that caught the 2833-file brace
rule in ADR-0046, and they did not care how confident its author was.

Two costs are accepted deliberately. An approver that fails closed will stall a run whenever
its authorization is unreadable, and that is the correct direction to fail. And an approver
that is never the author means work an agent wrote itself still waits for someone else —
which is a real limit, not an oversight: on the evidence above, it is the specific limit
that catches what coverage cannot.

## Alternatives considered

**Leave the human checkpoint in place.** Honest, and what happened that night: seven pull
requests sat green for hours until a person woke up. It makes unattended runs a misnomer and
spends a human's attention on the one step that 12.e says should be automated *around*.

**Let the agent approve its own work under authorization.** Simplest, and rejected on the
night's own evidence: 2512 tests at 100% coverage did not catch an `ImportError` the author
introduced, and an independent reader did. Self-approval removes the reader that worked.

**Weaken the gate so green checks merge without any review.** Rejected under 12.d — a gate
the operator relies on being routed around is exactly what a standing grant never covers —
and because the gate's failures that night were informative rather than obstructive.

**Require two independent agent approvals.** Stronger, and available later by narrowing the
grant; not adopted now because there is one reviewer lane running and mandating two would
make the rule unsatisfiable, which is a gate that cannot pass rather than a gate that binds.
