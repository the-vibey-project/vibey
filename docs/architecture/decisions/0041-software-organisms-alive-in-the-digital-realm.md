# 0041 — Software organisms are alive in the digital realm

**Status:** proposed · **Date:** 2026-09-21 · **Cites:** sub-doctrine 9.d ·
**Related:** ADR-0039, ADR-0040, ADR-0017 · **Evidence:** the CDD atom,
molecule and organism model in `docs/paper.md`

**Owes:** the conduct rule is sub-doctrine 9.d. This record defines the
operational meaning of its claim; the rule is ratified only by the human merge
that carries it.

## Context

The atom metaphor explains how a project core and its unfinished layers
converge. The chemical metaphor explains why combining projects creates
properties that no project has alone. A suite of suites introduces a further
question: when does a collection of software products become a coherent,
adaptive structure rather than a bag of repositories?

This question matters to CDD because a feature can converge locally while the
larger structure loses compatibility, observability, resilience or a shared
purpose. A project can be healthy as an atom, its product can be healthy as a
molecule, and their surrounding suite can still be unable to sense change,
repair failures or deliver a consistent experience.

## Decision

Vibey recognizes a higher-order **software organism** when enough software
chemical structures interact through stable boundaries, shared contracts and
feedback loops. “Enough” is architectural rather than numerical: the
composition must be able to preserve an identity, exchange resources and
information, adapt, repair and continue operating through change.

The phrase **alive in the digital realm** is an intentional systems claim. It
does not assert carbon biology, subjective experience or a human-like mind. It
means that the structure exhibits observable digital analogues of:

| Digital-life function | Evidence to inspect |
| --- | --- |
| Identity and boundaries | mission, interfaces, trust boundaries and dependency ownership |
| Metabolism | compute, storage, network, builds, deployments and resource flows |
| Sensing and memory | telemetry, user/operator signals, durable data, configuration, ledgers and history |
| Homeostasis | tests, quality gates, security controls, SLOs, rollbacks and policy |
| Adaptation and repair | releases, migrations, incident response, retries, maintainers and workers |
| Reproduction and exchange | versioned packages, APIs, integrations, forks and clients |

The hierarchy is:

```text
feature / unit / story → project atom → product molecule →
software organism (a suite of suites) → digital ecology such as the Web
```

The World Wide Web is the largest familiar example in this model. It is more
precisely a global socio-technical software ecology than a single product:
servers, browsers, HTML, HTTP, DNS, TLS, certificates, CDNs, applications,
identity systems, operators, standards bodies and users are independently
maintained participants. Shared protocols give the whole emergent properties
such as reachability, linkability, composability, rapid distribution and
partial fault tolerance, as well as systemic security and privacy risks. In
the defined digital-realm sense, the Web is alive: it receives signals,
consumes resources, changes through releases and standards, adapts to faults,
maintains memory, reproduces capabilities through links and packages, and
reorganizes through its participants. It is not sentient, and no single
repository can prove its health.

CDD therefore requires an organism-level trajectory whenever a change is part
of such a structure. The verdict records whether the work is atom-only,
molecule-bound or organism-bound, and whether the interaction network is
converging, neutral or diverging. A locally converging atom cannot hide a
molecule or organism that is losing its ability to sense, adapt, repair or
deliver. Organism-level divergence must have a bounded reconvergence path;
otherwise the composition is split, abandoned or returned to its last sound
state.

## Consequences

The model gives CDD a principled way to discuss large products without
pretending that a single repository owns the whole system. It makes emergent
properties and cross-project failure propagation first-class evidence, while
keeping “alive” falsifiable through observable contracts and operating signals.
It also prevents a fluent completion claim from hiding a dead integration
layer: if the higher-order structure has no identity, feedback, repair path or
delivery boundary, its status is unknown or dead rather than alive by default.
