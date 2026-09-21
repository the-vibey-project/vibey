# 0039 — Convergence-Driven Development (CDD) encloses specification and test-driven development

**Status:** proposed · **Date:** 2026-09-21 · **Cites:** sub-doctrine 9.c · **Related:** ADR-0016, ADR-0023, ADR-0020 · **Evidence:** the Qwen storm record at `src/vibey_tools/gh/docs/qwenloop-storm-2026-09-20.json`

**Owes:** the conduct rule is sub-doctrine 9.c. This record explains the
mechanism that makes the rule operational; the rule itself is ratified only by
the human merge that carries it.

## Context

Specification-Driven Development (SDD) makes intent explicit. Test-Driven
Development (TDD) turns part of that intent into executable checks. Neither
one, by itself, guarantees that an autonomous worker has changed the right
repository, used the repository's real stack, run the checks, cleaned up its
exploration, or produced a deliverable that can be handed to a reviewer.

The local Qwen storm made the missing abstraction visible. At the evidence
cutoff it had twelve allocated run directories, but only three runs had both a
verdict and the completion marker. A later non-empty run consumed its full
forty-turn limit and ended in `failed` without a verdict. The same operational
period also produced an untracked Go/platform draft and a separate untracked
Python skeleton in a repository whose tracked workspace is Python. Those files
were activity, not evidence that the requested features existed in the actual
Vibey codebase.

The problem is therefore not only whether a specification exists or whether a
test passes. It is whether each iteration reduces the distance between intent,
implementation, executable evidence and deliverable repository state.

## Decision

Vibey adopts **Convergence-Driven Development (CDD)** as the enclosing method
for every software change. CDD always sits on top of SDD and TDD:

1. SDD states the user intent, constraints and acceptance criteria.
2. TDD expresses the criteria as executable tests, properties or checks.
3. CDD grounds the work in the actual tracked repository, implements the
   smallest appropriate change, executes the checks, reviews the resulting
   state, and iterates until the delivery evidence closes every criterion.

The CDD state of an item is measured against four evidence sets:

```text
R = {acceptance criteria, implementation, executable checks, delivery state}
D(R) = unverified criteria + failing checks + unresolved blockers
       + unreviewed or unrelated repository changes
```

CDD measures that distance at four nested scopes: the overall project vision,
the phase or milestone vision, the feature set or epic, and the feature, unit or
user story. They are concentric views of one delivery state. A story that gets
greener while its epic acquires an unrelated platform, its milestone loses its
language boundary, or its project cannot publish is not a convergent feature.
The implementation may describe these as lower-energy states, but “energy” is
not left metaphorical: it means a lower unresolved-work distance at every
scope. Unknown parent context remains unknown and is reported, never invented.

The atom metaphor is retained as the teaching model. The nucleus is the core
software confirmed to work at the required quality and to do what it is meant
to do. The four CDD scopes are electron orbitals around that nucleus: active
layers of a living project being pulled toward lower unresolved-work energy.
“Nucleus-only” is terminal, not aspirational: it means either that the project
is complete and needs no further change, or that it is dead and no longer
maintained long-term. A maintained project with outstanding work is still an
atom with active orbitals, even when its core is healthy.

Multiple project atoms may compose a software chemical structure: a product,
platform or portfolio. Its properties are emergent from the interactions among
the atoms—interfaces, dependencies, data ownership, security boundaries,
release timing and operational contracts—not merely the sum of their features.
CDD therefore evaluates both each atom's convergence and the molecule's
interaction distance; a composition that raises divergence must have a bounded
reconvergence path or be abandoned.

When enough software chemicals interact in the right ways, they form a
higher-order biological structure: a software organism. “Enough” is
architectural, not a repository count: the composition must have stable
boundaries, feedback loops and shared contracts that preserve identity, move
resources and information, adapt, repair and continue operating through change.
Under this decision, that structure is **alive in the digital realm** when its
identity and boundaries, resource metabolism, sensing and memory, homeostasis,
adaptation and repair, and reproduction or exchange are observable in its
interfaces, telemetry, data, releases, controls and operating practices. This
is a deliberate systems claim about digital life, not a claim of carbon biology
or subjective experience.

The hierarchy is therefore item or story → project atom → product molecule →
software organism (a suite of suites) → a digital ecology such as the World
Wide Web. The Web is the largest familiar example: independently maintained
servers, browsers, protocols, standards, applications, identity systems,
operators and users interact to produce reachability, composability,
adaptation and partial fault tolerance that no single repository contains. CDD
must inspect these higher-order interactions when they are in scope. A locally
converging atom cannot hide a molecule or organism that is losing its ability to
sense, adapt, repair or deliver; such divergence requires a bounded
reconvergence path or the composition is split or abandoned.

An iteration is *converging* when it decreases `D(R)`, or when a bounded
discovery step replaces an unknown with a concrete criterion, test or blocker.
It is *neutral* when it preserves the state while gathering necessary evidence.
It is *diverging* when it increases unresolved work, leaves the target stack,
adds unrelated artifacts, or loses a previously established fact. A small
divergence is allowed only if the iteration names its bounded size and the
following step that returns to a lower `D(R)`. A large divergence or one with
no reconvergence path is discarded, and the item returns to its last sound
state. No volume of edits, tool calls, tokens, or model confidence is evidence
of convergence.

The minimum CDD completion record contains:

- each acceptance criterion mapped to code and an executable check;
- the actual tracked manifests, language and package boundary used;
- the focused and relevant broader checks, with their observed results;
- a trajectory classification and, when applicable, the reconvergence path;
- a diff and working-tree review showing no unrelated audit, storm, cache or
  generated artifacts;
- a Conventional Commit or an explicit commit-ready handoff; and
- when remote publication is in scope, the pushed head and pull-request
  evidence.

An autonomous worker may prepare a local commit according to its invocation
mode, but remote push and pull-request creation remain separate, explicitly
authorized mutations. Neither a plan, a verdict, a done marker nor a generated
file can substitute for the missing evidence.

## Qwen storm implementation

`qwenloop` applies CDD at the item boundary. It derives a read-only repository
context from `git ls-files`, includes that context in each one-item plan, and
instructs the model to preserve the existing language and package layout. A
storm completion requires the verdict fields `criteria`, `tests`, `repository`,
`levels`, `trajectory`, `composition` and `delivery`, in addition to the existing tool-call, progress and
done-marker contract. A failed item receives a bounded number of repair
iterations and the storm does not advance to the next item until the current
item converges or is reported as blocked.

This is deliberately a guardrail, not a claim that text alone proves a feature.
The repository checks, test results, diff review and remote checkpoint remain
the evidence that a reviewer must verify. CDD makes the missing evidence a
failure state instead of letting a locally fluent run call itself complete.

## Alternatives rejected

- **SDD only.** A well-written issue still permits implementation in the wrong
  repository, language or package boundary.
- **TDD only.** A green test can cover a partial or misplaced implementation and
  says nothing about unrelated generated artifacts or remote delivery.
- **Treat every edit as progress.** The storm logs show why this is unsafe:
  generated files and long transcripts can increase distance from the feature.
- **Permit unbounded autonomous retries.** Repeating a divergent attempt burns
  capacity and compounds artifacts. Repair is bounded and remains on the same
  item.
- **Let a completion marker close the item.** A marker is a protocol signal;
  evidence-bounded status and the CDD fields are required as well.

## Consequences

CDD adds a small amount of ceremony to every autonomous change: repository
grounding, trajectory classification, evidence fields and repair checkpoints.
That cost is intentional. It makes wrong-stack work, unbounded exploration and
false completion visible early, while preserving the existing no-network and
operator-controlled publication boundary of local runners. The method also gives
the paper a falsifiable operational claim: a future storm can report the number
of items whose evidence distance decreased, stayed neutral, diverged and
reconverged, or terminated blocked.
