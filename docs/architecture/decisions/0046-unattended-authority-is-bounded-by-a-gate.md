# 0046 — Standing authority to act unattended is bounded by a gate a human defined, never by the agent's own judgement

**Status:** proposed · **Date:** 2026-09-22 · **Cites:** sub-doctrines 12.b, 12.c, 12.d which this record implements, and 10.f · **Related:** ADR-0020, ADR-0028, ADR-0039, ADR-0045 · **Evidence:** the QwenStorm run of 2026-09-22–23, in which fifteen lanes finished `completed` and none was publishable; the repairs and refusals are in `docs/plans/qwenstorm-3.0.0/tools/lane-repair.py` and the run log in `progress.log`

**Owes:** nothing new as conduct — 12.d is the conduct and is ratified separately (ADR-0020:
the record argues, the canon states). It owes the advertised ADR count in `CLAUDE.md`,
`AGENTS.md`, `GEMINI.md`, `README.md` and `docs/index.md` (`tests/meta/test_adr_counts.py`),
and a nav entry in `properdocs.yml`.

## Context

The operator sleeps. The storm does not. On the night of 2026-09-22 the operator granted
standing authority for the reviewing agent to repair finished lanes unattended — including
the judgement-level repairs the repair script deliberately refuses, because a *script* must
not invent code with nobody watching while an agent reviewing a lane is precisely the role
the pipeline was designed around.

That grant is the useful thing and also the dangerous one. Every property that makes it
valuable — no round trip to a human, no waiting until morning, latitude to decide what a
defect actually is — is a property that makes an overreach cheap and invisible. The failure
mode is not an agent doing something forbidden. It is an agent doing something *plausible*
that the operator would not have chosen, in a place the operator will not think to look,
and reporting it as done.

Three things from that night make the shape concrete:

- A repair rule written that night deleted every line consisting only of `}`, on the stated
  reasoning that "Python has no closing brace". That is false — dicts and sets use them — and
  across the lanes the rule touched 2833 files that had nothing wrong with them. What caught
  it was not the agent's judgement. It was an all-or-nothing revert gated on the file still
  importing afterwards: a mechanism, written in advance, that did not care how confident the
  rule's author was.
- A lane (`rmq-r01-queue-config`) had *deleted* three working Protocol interfaces that its
  package's `__init__.py` imports, and added five referencing dataclasses that do not exist.
  Repairing it would have meant writing the spec the lane failed to write. The right answer
  was to revert and re-queue, and only a bound that distinguishes "repair" from "author"
  makes that answer reachable.
- Another lane (`rmq-r02-wakeup-composition`) had done genuinely good work — tightening
  `object` return types to real ones — buried under transcript debris. Reverting it wholesale
  would have discarded the value; adopting it wholesale would have made a composition-root
  protocol import concrete implementations, which is the one thing that file exists to avoid.

## Decision

Standing authority to act unattended is bounded by a check a human defined, and never by the
acting agent's own assessment of its work.

For this repository that check is the one already ratified in ADR-0028: work reaches
`develop` only as a pull request whose head carries a successful `PR automation / gate`, and
the merge train is what merges it. An agent acting overnight may write freely inside a lane's
own clone; it may not write `develop` or `main` directly, may not merge its own work, and may
not route around the gate — not with `--no-verify`, not with `--admin`, not by any means
whose purpose is to make a check stop applying.

Three consequences follow, and they are the point rather than caveats:

1. **The bound is mechanical, not attitudinal.** "Be careful" is not a bound. A revert that
   fires when a file still will not import is a bound, because it holds when the agent is
   wrong *and* confident. Every unattended repair here is verified by re-running the same
   check that was holding the work, never by a second standard the agent chose.
2. **Repair and authorship are different acts.** Adding the import the file next door already
   uses is bookkeeping; supplying the definition that import was meant to find is the work.
   The line is not difficulty — it is whether a reviewer would be reading a diff somebody
   decided to write. Where the lane's work is net-negative the answer is revert and re-queue,
   not rescue.
3. **Declining is a reportable outcome.** An agent that says "six lanes were held, I repaired
   four and these two need you, here is why" has done the job. Silence about the refusals is
   the failure, because it is the refusals that tell the operator where the system is actually
   weak — on this night, that the local model emits modules which do not import, which no
   amount of repair tooling addresses.

## Consequences

The operator can hand over the night without handing over the branch. The blast radius of a
mistaken repair is one pull request, reviewable in the morning in the place pull requests are
already reviewed, rather than a commit on `develop` nobody was awake for.

The cost is that unattended work cannot land faster than the gate, and a green gate is not
proof the repair was *right* — only that it did not break what the gate covers. That is the
correct trade and the honest claim: the gate bounds the damage, the morning review judges the
work, and neither is skipped because the other happened (10.f).

It also means a grant must be written down to be citable later. A standing authority that
lives only in a chat log cannot be held against the agent that exceeded it, nor relied on by
the agent that honoured it — which is 12.b applied to permission rather than to policy.
