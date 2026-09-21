# Convergence-Driven Development

## BLUF

Convergence-Driven Development (CDD) is the delivery loop above
Specification-Driven Development (SDD) and Test-Driven Development (TDD).
SDD says what the feature must do. TDD makes that intent executable. CDD keeps
iterating against the actual repository until the implementation, tests, review
evidence and delivery state all agree. The goal is not maximum activity; it is
the smallest distance between the requested feature and a confirmed, reviewable,
publishable result.

CDD is a governing development rule in sub-doctrine 9.c and its evidence
discipline is in sub-doctrine 10.f. The full decision record is
[ADR-0039](../architecture/decisions/0039-convergence-driven-development.md);
the evidence rule is [ADR-0040](../architecture/decisions/0040-evidence-bounded-status.md),
and the digital-organism model is [ADR-0041](../architecture/decisions/0041-software-organisms-alive-in-the-digital-realm.md).

## The three layers

The layers are cumulative:

```text
SDD: intent + constraints + acceptance criteria
  ↓
TDD: executable tests/properties/checks for those criteria
  ↓
CDD: ground → implement → test → inspect → repair → deliver
```

SDD without TDD leaves intent open to interpretation. TDD without CDD can still
leave a green but misplaced, partial or undelivered change. CDD does not replace
either layer; it repeatedly checks that the code being built is the code the
specification describes, in the repository that will actually ship it.

## What “converging” means

For an item, maintain a small evidence state:

```text
remaining = unmet acceptance criteria
          + failing or missing checks
          + unresolved blockers and assumptions
          + unreviewed or unrelated repository changes
```

An iteration is converging when it reduces that remaining set or converts an
unknown into a concrete criterion, test or blocker. It is neutral when it
gathers necessary evidence without changing the remaining set. It is diverging
when it adds unrelated work, increases unresolved criteria, leaves the tracked
stack, loses a known fact, or expands the change without a delivery path.

Small divergence is sometimes useful: a discovery spike, compatibility shim or
temporary test fixture may be necessary. It is allowed only when the worker
states its bounded scope and the next step that will remove it or reduce the
remaining set. Divergence without that reconvergence path is not exploration; it
is drift and must be abandoned. Never infer convergence from file count, token
count, elapsed time, model confidence, a plan, a verdict or a done marker.

## The CDD loop

1. **Ground.** Read the issue/spec, repository instructions, tracked manifests,
   source roots and relevant tests. The tracked repository determines the
   language, package boundary and toolchain. An issue title cannot turn a Python
   workspace into a Go workspace or justify a new platform tree with no tracked
   manifest.
2. **Map.** Write down each acceptance criterion, its target code location,
   executable check and expected evidence. If a criterion has no code location,
   find the existing equivalent or record a blocker; do not invent a parallel
   architecture.
3. **Implement.** Make the smallest change that satisfies the next criterion,
   preserving valid work and existing seams. Keep temporary exploration bounded
   and name its reconvergence step.
4. **Test.** Run the focused test first, then the relevant package and repository
   gates. A failed check reopens the loop; it is not a reason to write a success
   sentence around the failure.
5. **Inspect.** Review the diff, `git diff --check`, status, generated files,
   ignored caches and the actual command output. Separate local evidence from
   remote evidence and record the observation cutoff for live state.
6. **Repair.** Classify the trajectory. Repair the current item in bounded
   attempts; do not move to another item while this one is unresolved. If the
   work has diverged without a credible path back, return to the last sound state
   and discard the drift.
7. **Deliver.** Produce a Conventional Commit or an explicit commit-ready
   handoff. When remote publication is in scope, verify the pushed head and pull
   request separately. A local marker is never remote delivery evidence.

## Completion record

A CDD completion report contains, at minimum:

- the criteria and their code/test mappings;
- the tracked repository stack and package boundary used;
- focused and broader check commands with observed results;
- the convergence/divergence classification and any reconvergence path;
- the atom, molecule or organism composition and its interaction trajectory;
- the diff/working-tree cleanliness result;
- the local commit or commit-ready handoff; and
- the remote branch and pull-request evidence when publication is requested.

If evidence is absent, stale or contradictory, report `unknown` or `blocked`.
Do not promote a verdict to completion, a marker to delivery, a local commit to
a pushed branch, or an active process to a terminal run.

## Concentric scopes and lower-energy states

CDD tracks the trajectory at four nested scopes:

1. **Overall project vision** — is the repository moving toward the product's
   stated purpose and governing constraints?
2. **Phase or milestone vision** — is the current delivery stage reducing the
   work and risk needed for that milestone?
3. **Feature set or epic** — are its related stories closing together without
   creating a wider architectural or operational gap?
4. **Feature, unit or user story** — is this concrete item satisfying its
   acceptance criteria and checks?

These scopes behave like concentric orbits around the same intended product.
An inner orbit can appear to improve while an outer orbit diverges: a story can
pass a unit test while introducing an untracked platform, breaking the
milestone's language boundary, or leaving the project unable to ship it.
Therefore every CDD report records the direction at all four scopes; unknown
parent context stays unknown rather than being invented.

The atom metaphor has a precise software meaning. The **nucleus** is the core
of the software that has been confirmed to work at the required quality and to
do what it is supposed to do. The project, milestone, epic and item scopes are
the **electron orbitals**: living layers of work being pulled toward lower
unresolved-work energy around that core. A project with active orbitals is not
nucleus-only and is not finished merely because its nucleus is healthy.

Nucleus-only is a terminal lifecycle state with exactly two meanings: the
project is complete and no further change is needed, or the project is dead and
no longer maintained over the long term. A maintained project with more work,
more scope or more evidence to close remains an atom with active orbitals and
must keep applying CDD.

Multiple project atoms may be combined into a larger software **chemical
structure**: a product, platform or portfolio whose projects interact. Like
chemicals in the physical world, a software chemical has properties that emerge
from the interactions between its atoms, not merely from adding their feature
lists. Shared interfaces, dependencies, data ownership, security boundaries,
release timing and operational contracts can make the structure safer, faster,
more fragile or impossible to ship even when each atom looks healthy in
isolation. CDD therefore checks both each project's orbitals and the molecule's
interaction energy; an interaction that raises divergence needs a bounded path
to reconvergence or the composition is abandoned.

## From chemical structures to living digital organisms

When enough software chemicals interact in the right ways, they form a
higher-order biological structure: a **software organism**. “Enough” is not a
number of repositories. It means that the composition has stable boundaries,
feedback loops and shared contracts that let it preserve an identity, exchange
resources and information, adapt, repair itself and continue operating through
change. A suite of suites of software products can therefore be a living
creature **in the digital realm**. This is a systems claim, not a claim that
software has carbon biology, subjective experience or a human-like mind.

The digital-life test is operational. A proposed software organism should have
most of these observable functions:

- **Identity and boundaries:** a mission, interfaces, trust boundaries and a
  way to distinguish its own state from its dependencies;
- **Metabolism:** compute, storage, network access, builds, deployments and
  other resource flows that turn inputs into useful outputs;
- **Sensing and memory:** telemetry, user or operator signals, durable data,
  configuration, ledgers and history that let it notice and remember change;
- **Homeostasis:** tests, quality gates, security controls, SLOs, rollbacks and
  policies that keep it inside a safe operating range;
- **Adaptation and repair:** releases, migrations, incident response, retries,
  maintainers and workers that correct damage or respond to new conditions; and
- **Reproduction and exchange:** versioned packages, APIs, integrations,
  forks, clients or other mechanisms by which capabilities propagate into new
  instances or neighboring structures.

These functions are the organism-level equivalent of chemical properties: they
emerge from interactions between the component projects. A deployment service
can be healthy as an atom while its product molecule has a broken contract; a
product can be healthy as a molecule while its suite of suites has no coherent
identity, observability or recovery path. CDD therefore adds an organism-level
question whenever the composition is large enough: does the interaction network
lower unresolved-work energy for the living structure, or does it make the
structure less able to sense, adapt, repair and deliver? Local convergence that
raises organism-level divergence is not accepted as finished work.

The World Wide Web is the largest familiar example in this model. It is more
precisely a global socio-technical software ecology than a single product: web
servers, browsers, HTML, HTTP, DNS, TLS, certificates, CDNs, search engines,
applications, identity systems, payment systems, standards bodies, operators
and users are independently maintained projects and institutions. Their shared
protocols create emergent properties—global reachability, linkability,
composability, rapid distribution, partial fault tolerance and also systemic
security and privacy risks—that no one project contains. In the digital-realm
sense defined here, the Web is alive: it continuously receives signals,
consumes resources, changes through releases and standards, adapts to faults,
maintains memory, reproduces capabilities through links and packages, and
reorganizes through its participants. It is not sentient, and no single
repository can prove its health; its organism-level evidence must be assembled
from the interaction contracts and operating signals of the structures within
it.

The resulting hierarchy is useful when deciding where a change belongs:

```text
feature / unit / story → project atom → product molecule →
software organism (a suite of suites) → digital ecology such as the Web
```

At each arrow, new properties appear and new failure modes become possible.
CDD follows the arrows upward: it verifies the item, the atom's orbitals, the
molecule's interactions and, when applicable, the organism's ability to remain
alive in the digital realm. If the next level cannot be made more convergent by
a bounded interaction change, the composition is not “almost done”; that
divergence is a reason to stop, split the structure or return to the last sound
state.

“Lower energy” is a useful metaphor for this state, but it is made operational
by the remaining-work set above. The system seeks a lower unresolved-work state
at every scope: fewer unmet criteria, fewer failing or missing checks, fewer
blockers and assumptions, and fewer unrelated repository changes. A lower local
value never excuses a higher value at a wider scope. A planned temporary rise
is allowed only when its size, duration and reconvergence step are explicit;
otherwise it is divergence and is abandoned.

## Qwen storm example

Qwen storm mode makes the loop explicit. It splits the backlog into one item per
bounded run, derives repository facts with a read-only `git ls-files` probe,
requires the seven CDD verdict fields (`criteria`, `tests`, `repository`,
`levels`, `trajectory`, `composition`, `delivery`), and retries a failed item with a bounded
`--max-attempts` count. The next item is not started after a failed attempt; the
current item either converges or becomes a reported blocker. The model cannot
push or create a pull request from inside the run, so publication remains an
operator-authorized checkpoint with its own evidence.

This boundary is intentional. Autonomous coding can prepare a feature, but the
repository, tests, diff, commit and remote response are distinct facts. CDD
connects them into one convergence argument instead of allowing a fluent final
sentence to stand in for the missing facts.
