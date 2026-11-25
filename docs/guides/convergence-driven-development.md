---
description: Convergence-Driven Development, vibey's delivery loop above specification and tests, and how to run it by hand or let vibey run it unattended.
---

# Deliver a change with Convergence-Driven Development

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** Convergence-Driven Development (CDD) is the loop around
> specification-driven and test-driven development: ground in the real repository, implement,
> test, inspect, repair, deliver, and repeat until the code, the tests, the review and the
> delivery state all agree. Every pass is judged converging, neutral or diverging, and drift with
> no way back is abandoned. It is the rule for every change here (sub-doctrine 9.c). Reading this
> page takes ten minutes.

## The lesson: closing the distance

Daniel had a green test run on his screen and a frown on his face.

**Daniel:** Professor, every test passes. Isn't the feature done?

**Professor Feynman:** Let me ask you about a builder. The client draws the house they want: that
is the specification. The builder writes a checklist from the drawing, "three bedrooms, a door
that locks": those are the tests. Now the builder ticks every box. Is the house built?

**Daniel:** Only if he built it on the right plot.

**Professor Feynman:** And with the right bricks, and handed over the keys. A ticked checklist on
the wrong plot is still the wrong house. CDD is the builder walking back to the drawing, again
and again, and asking "how far is what stands here from what was asked for?" Each visit, the
distance should shrink.

**Daniel:** How do you measure the distance?

**Professor Feynman:** Count what is left: criteria not met, checks failing or missing, blockers
and guesses not resolved, and changes in the repository that have nothing to do with the job.
If a pass makes that list shorter, or turns a vague worry into a concrete test, it is converging.
If it gathers facts without changing the list, it is neutral. If it makes the list longer, or wanders
off, it is diverging.

**Daniel:** Is diverging always wrong? Sometimes I have to try something to learn.

**Professor Feynman:** Good, that is the gap. A short detour is allowed, if you say how big it is
and how you will come back. A detour with no way back is not exploring; it is drift, and you throw
it away. And never count the distance by how busy you were: not files, not tokens, not hours, and
not how confident the model sounded. My builder picture stops working in one place: a house is
finished once. Software that is still maintained always has a next list.

## The lesson: rings around a core

The next morning, over the same desk, Daniel came back with a second question.

**Daniel:** You said to judge the whole project, not just the item. Why?

**Professor Feynman:** Because a small thing can improve while a big thing gets worse. A story can
pass its test while it adds a language the project never used, or breaks the release. So we look
at four rings at once: the whole project, the current milestone, the epic, and the item.

**Daniel:** Like an atom, with rings around the middle.

**Professor Feynman:** That is the picture the project uses. The middle, the nucleus, is the part
already proven to work. The rings are the open work, being pulled in. A project with open rings is
not finished, however healthy its middle. "Only a nucleus" means one of two things: the project is
complete, or it is dead.

## Do it

Checked against this repository at develop `d91a3791e` with vibey-engine 0.4.0.

### By hand, for one change

1. **Ground.** Read the issue, the repository's instructions, the tracked manifests and the tests
   near the change. The tracked repository decides the language and toolchain, not the issue
   title.

   ```bash
   git ls-files | head
   ```

   You should see the tracked files, which is what the change must fit into.

2. **Map.** Write each acceptance criterion beside the file it touches and the check that proves
   it. A criterion with no code location is a blocker to record, not a reason to invent a new
   structure.

3. **Implement** the smallest change that meets the next criterion.

4. **Test.** Run the focused test first, then the package and repository gates (the commands are
   in `CONTRIBUTING.md`). A failed check reopens the loop.

5. **Inspect.** Look at the real diff and status, not a summary of them.

   ```bash
   git diff --check
   git status --short
   ```

   You should see nothing from `git diff --check` (it exits 0 when there is no whitespace damage),
   and only the files you meant to change from `git status --short`.

6. **Repair.** Judge the pass converging, neutral or diverging. Fix this item in bounded attempts
   before you start another; if it has drifted with no way back, return to the last sound state.

7. **Deliver.** Make a Conventional Commit, or hand over a commit-ready change. When publishing is
   in scope, check the pushed branch and the pull request separately: a local commit is not a
   pushed branch.

### Let vibey run the loop

vibey applies the same loop to its own runs. These are the ways to run it unattended:

| Command | What it does |
|---|---|
| `vibey worker --autonomous` | Turns on every switch that is safe to leave on unattended (`--auto-answer`, `--auto-accept-all`, `--auto-record-research-gaps`) for one worker and one project. Never publishing, never a deployment, never a spending gate. |
| `vibey ultra start` | Runs a project's BUILD passes with no turn limit, pass after pass ([ADR-0063](../architecture/decisions/0063-ultra-effort-without-a-ceiling.md)). `vibey ultra status` shows passes, cap and spend; `vibey ultra stop` stops at the next pass. |
| `gptossloop run --storm` or `qwenloop run --storm` | The local runner's storm mode: one bounded run per backlog item, with a CDD verdict for each (below). |

Before any BUILD work runs, vibey slices a large plan into the CDD layers
([ADR-0092](../architecture/decisions/0092-large-tasks-are-sliced-into-the-cdd-layers-before-they-run.md),
proposed): a plan of up to 8 items is stories only; larger plans are grouped into epics, then
phases, then projects, never more than four layers. A group runs to completion before the next
begins, and each item's place is recorded in its job as `slice_path`
(`src/vibey/domain/slicing.py`, used by `application/build_decompose_handler.py`).

## Daniel's teach-back

**Daniel:** SDD says what to build and TDD makes it checkable, but CDD keeps comparing the real
repository with both until they agree. I measure the distance by what is left, not by how much I
did, and I judge every pass converging, neutral or diverging. A detour needs a stated size and a
way back. I check all four rings, project down to item, and I report unknown when I have no
evidence.

**Professor Feynman:** Exactly. One more thing to hold on to: a verdict, a marker or a confident
final sentence is never the evidence. The test output, the diff and the remote are.

## The three layers

The layers are cumulative:

```text
SDD: intent + constraints + acceptance criteria
  ↓
TDD: executable tests/properties/checks for those criteria
  ↓
CDD: ground → implement → test → inspect → repair → deliver
```

SDD without TDD leaves intent open to interpretation. TDD without CDD can still leave a green but
misplaced, partial or undelivered change. CDD does not replace either layer; it repeatedly checks
that the code being built is the code the specification describes, in the repository that will
actually ship it. The goal is not maximum activity; it is the smallest distance between the
requested feature and a confirmed, reviewable, publishable result.

## What "converging" means

For an item, keep a small evidence state:

```text
remaining = unmet acceptance criteria
          + failing or missing checks
          + unresolved blockers and assumptions
          + unreviewed or unrelated repository changes
```

- **Converging:** the pass reduces that remaining set, or turns an unknown into a concrete
  criterion, test or blocker.
- **Neutral:** it gathers necessary evidence without changing the remaining set.
- **Diverging:** it adds unrelated work, increases unresolved criteria, leaves the tracked stack,
  loses a known fact, or expands the change without a delivery path.

Small divergence is sometimes useful: a discovery spike, a compatibility shim or a temporary test
fixture. It is allowed only when the worker states its bounded scope and the next step that will
remove it or reduce the remaining set. Divergence without that path back is drift and must be
abandoned. Never infer convergence from file count, token count, elapsed time, model confidence,
a plan, a verdict or a done marker.

## The CDD loop in full

1. **Ground.** Read the issue or spec, repository instructions, tracked manifests, source roots and
   relevant tests. The tracked repository determines the language, package boundary and
   toolchain. An issue title cannot turn a Python workspace into a Go workspace or justify a new
   platform tree with no tracked manifest.
2. **Map.** Write down each acceptance criterion, its target code location, executable check and
   expected evidence. If a criterion has no code location, find the existing equivalent or record
   a blocker; do not invent a parallel architecture.
3. **Implement.** Make the smallest change that satisfies the next criterion, preserving valid work
   and existing seams. Keep temporary exploration bounded and name its reconvergence step.
4. **Test.** Run the focused test first, then the relevant package and repository gates. A failed
   check reopens the loop; it is not a reason to write a success sentence around the failure.
5. **Inspect.** Review the diff, `git diff --check`, status, generated files, ignored caches and the
   actual command output. Separate local evidence from remote evidence and record the observation
   cutoff for live state.
6. **Repair.** Classify the trajectory. Repair the current item in bounded attempts; do not move to
   another item while this one is unresolved. If the work has diverged without a credible path
   back, return to the last sound state and discard the drift.
7. **Deliver.** Produce a Conventional Commit or an explicit commit-ready handoff. When remote
   publication is in scope, verify the pushed head and pull request separately. A local marker is
   never remote delivery evidence.

## The completion record

A CDD completion report contains, at minimum:

- the criteria and their code and test mappings;
- the tracked repository stack and package boundary used;
- focused and broader check commands with observed results;
- the convergence or divergence classification and any reconvergence path;
- the atom, molecule or organism composition and its interaction trajectory;
- the diff and working-tree cleanliness result;
- the local commit or commit-ready handoff; and
- the remote branch and pull-request evidence when publication is requested.

If evidence is absent, stale or contradictory, report `unknown` or `blocked`. Do not promote a
verdict to completion, a marker to delivery, a local commit to a pushed branch, or an active
process to a terminal run (sub-doctrine 10.f,
[ADR-0040](../architecture/decisions/0040-evidence-bounded-status.md)).

## Four nested scopes

CDD tracks the trajectory at four nested scopes:

1. **Overall project vision:** is the repository moving toward the product's stated purpose and
   governing constraints?
2. **Phase or milestone vision:** is the current delivery stage reducing the work and risk needed
   for that milestone?
3. **Feature set or epic:** are its related stories closing together without creating a wider
   architectural or operational gap?
4. **Feature, unit or user story:** is this concrete item satisfying its acceptance criteria and
   checks?

An inner scope can appear to improve while an outer one diverges: a story can pass a unit test
while introducing an untracked platform, breaking the milestone's language boundary, or leaving the
project unable to ship it. So every CDD report records the direction at all four scopes; unknown
parent context stays unknown rather than being invented.

## Atoms, molecules and organisms

The atom picture has a precise software meaning. The **nucleus** is the core of the software that
has been confirmed to work at the required quality and to do what it is supposed to do. The
project, milestone, epic and item scopes are the **electron orbitals**: living layers of work being
pulled toward lower unresolved-work energy around that core. A project with active orbitals is not
nucleus-only and is not finished merely because its nucleus is healthy.

Nucleus-only is a terminal lifecycle state with exactly two meanings: the project is complete and
no further change is needed, or the project is dead and no longer maintained. A maintained project
with more work, more scope or more evidence to close remains an atom with active orbitals and must
keep applying CDD.

Several project atoms may combine into a software **chemical structure**: a product, platform or
portfolio whose projects interact. Its properties emerge from the interactions between its atoms,
not merely from adding their feature lists. Shared interfaces, dependencies, data ownership,
security boundaries, release timing and operational contracts can make the structure safer,
faster, more fragile or impossible to ship even when each atom looks healthy alone. CDD checks both
each project's orbitals and the molecule's interactions; an interaction that raises divergence
needs a bounded path to reconvergence, or the composition is abandoned.

When enough software chemicals interact through stable boundaries, feedback loops and shared
contracts, the project calls the result a **software organism**: a suite of suites that keeps an
identity, exchanges resources and information, adapts, repairs itself and keeps operating through
change. "Enough" is architectural, not a repository count. This is a systems lens, not a claim that
software has carbon biology, subjective experience or a human-like mind (sub-doctrine 9.d,
[ADR-0041](../architecture/decisions/0041-software-organisms-alive-in-the-digital-realm.md)). A
proposed organism should show most of these observable functions:

- **Identity and boundaries:** a mission, interfaces, trust boundaries and a way to tell its own
  state from its dependencies';
- **Metabolism:** compute, storage, network, builds, deployments and other resource flows that turn
  inputs into useful outputs;
- **Sensing and memory:** telemetry, user and operator signals, durable data, configuration,
  ledgers and history;
- **Homeostasis:** tests, quality gates, security controls, service objectives, rollbacks and
  policies that keep it inside a safe operating range;
- **Adaptation and repair:** releases, migrations, incident response, retries, maintainers and
  workers that correct damage or respond to new conditions; and
- **Reproduction and exchange:** versioned packages, APIs, integrations, forks, clients or other
  ways capabilities propagate.

A deployment service can be healthy as an atom while its product molecule has a broken contract; a
product can be healthy as a molecule while its suite of suites has no coherent identity,
observability or recovery path. So when a composition is large enough, CDD asks one more question:
does the interaction network lower unresolved work for the whole, or make it less able to sense,
adapt, repair and deliver? Local convergence that raises divergence at the organism is not accepted
as finished work.

The project reads the World Wide Web as the largest familiar example, more precisely a global
socio-technical ecology than a single product: servers, browsers, HTML, HTTP, DNS, TLS,
certificates, CDNs, search engines, applications, identity and payment systems, standards bodies,
operators and users are independently maintained projects and institutions whose shared protocols
create properties none of them contains. Read through this lens, the Web is alive in the digital
realm: it receives signals, consumes resources, changes through releases and standards, adapts to
faults, keeps memory, reproduces capabilities through links and packages, and reorganises through
its participants. That is an interpretation, not a measurement; nothing in vibey measures it, and
no single repository can prove the Web's health. The full lens is
[the biological philosophy](biological-philosophy.md).

The hierarchy helps decide where a change belongs:

```text
feature / unit / story → project atom → product molecule →
software organism (a suite of suites) → digital ecology such as the Web
```

At each arrow, new properties and new failure modes appear. CDD follows the arrows upward: it
verifies the item, the atom's orbitals, the molecule's interactions and, when it applies, the
organism's ability to keep working. If the next level cannot be made more convergent by a bounded
interaction change, the composition is not "almost done"; that divergence is a reason to stop,
split the structure or return to the last sound state.

"Lower energy" is a metaphor made operational by the remaining-work set above. The aim is a lower
unresolved-work state at every scope: fewer unmet criteria, fewer failing or missing checks, fewer
blockers and assumptions, and fewer unrelated repository changes. A lower local value never excuses
a higher value at a wider scope. A planned temporary rise is allowed only when its size, duration
and reconvergence step are explicit; otherwise it is divergence and is abandoned.

## The local runner's storm mode

The local runner (the package that ships `gptossloop` and `qwenloop`) has a storm mode that makes
the loop explicit, `run --storm`:

- It splits the backlog into one item per bounded run, across the repositories it discovers (or
  those named with `--repo`).
- It derives repository facts with a fixed, read-only `git ls-files -z` probe
  (`src/vibey_runners/qwen/src/qwenloop/cli/app.py`).
- It requires the seven CDD verdict fields in every item's final verdict: `criteria`, `tests`,
  `repository`, `levels`, `trajectory`, `composition` and `delivery`
  (`src/vibey_runners/qwen/src/qwenloop/application/storm.py`).
- It retries a failed item up to `--max-attempts` times (default 3, at most 10). The next item is
  not started after a failed attempt; the current item either converges or becomes a reported
  blocker.
- Its prompt tells the model that pushing and opening a pull request remain an operator-authorized
  step, so publication keeps its own evidence.

This boundary is intentional. Autonomous coding can prepare a feature, but the repository, tests,
diff, commit and remote response are distinct facts. CDD connects them into one convergence argument
instead of letting a fluent final sentence stand in for the missing facts.

## Where the rule is written

- Sub-doctrine 9.c (the loop) and 10.f (evidence-bounded status), in
  [the canon](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/docs/doctrines.md).
- [ADR-0039](../architecture/decisions/0039-convergence-driven-development.md), the decision.
- [ADR-0040](../architecture/decisions/0040-evidence-bounded-status.md), the evidence rule.
- [ADR-0041](../architecture/decisions/0041-software-organisms-alive-in-the-digital-realm.md), the
  organism model.

vibey is a work in progress; the project announces milestones on its
[Discord server](https://discord.gg/Qvu8aYnVS).

## When it goes wrong

| What you see | What it means | What to do |
|---|---|---|
| Tests pass but the change adds a new language or platform tree | The item converged while the project diverged. | Return to the tracked stack; record a blocker if the criterion truly needs something new. |
| A storm item keeps failing until `--max-attempts` runs out | The item did not converge in bounded attempts. | Read its reported blocker; it is not skipped silently, and the next item waits. |
| A report says "done" with no command output | A verdict was promoted to completion. | Report `unknown` until the test output, diff and remote evidence exist. |
| A detour keeps growing | Divergence with no stated way back. | State its size and the step that removes it, or discard it and return to the last sound state. |

## Where next

- [The biological philosophy](biological-philosophy.md), for the atom, molecule and organism lens in
  full.
- [Publishing a finished project](publishing.md), for the delivery step that sends work off the
  machine.
- [Contributing](https://github.com/the-vibey-project/vibey/blob/develop/CONTRIBUTING.md), for the
  exact gates to run in the test step.

## Say it in one line

CDD means: measure what is left, not what you did; judge each pass converging, neutral or
diverging; check every scope; and call nothing done without evidence.
