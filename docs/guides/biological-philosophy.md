# The biological philosophy

Vibey's development loop, Convergence-Driven Development (CDD), measures delivery as a
scoreboard: work converges, stays neutral or diverges, and divergence needs a bounded path
back. This page sets out the broader philosophy the project builds on that scoreboard. It
reads software as having structure at several scales, from a single project up to the
whole Web, and it names the study of that structure **Biodigitology**.

The research paper does not rely on this philosophy and does not argue for it. The paper
keeps CDD only as a scoreboard, in its Discussion, and points here for the rest. The
decision behind this page is [ADR-0041](../architecture/decisions/0041-software-organisms-alive-in-the-digital-realm.md),
and its conduct rule is sub-doctrine 9.d in the governance canon.

## The atom

A project is drawn as an atom.

- **The nucleus** is the core software already confirmed to work at high quality and to do what it is supposed to do.
- **The orbitals** are the four CDD scopes (item, epic, phase, project): living layers of open work, pulled toward the nucleus as delivery lowers their unresolved work.

A project with active orbitals is not nucleus-only, even when its nucleus is healthy.
Nucleus-only is a terminal state with exactly two meanings. Either the project is complete
and needs no further change, or it is dead and no longer maintained. A maintained project
with outstanding scope or evidence is an atom with active orbitals and keeps running the
loop.

## The molecule

Several projects combine their atoms into a software chemical structure: a product, a
platform or a portfolio. As in chemistry, the structure has properties that come from the
interactions among its atoms, not just the sum of their features. Interfaces,
dependencies, data ownership, security boundaries, release timing and operational
contracts are the bonds. A bond can lower or raise the molecule's unresolved work; strain
in a bond, such as schema drift, needs a bounded path back to convergence, or the
composition is abandoned. CDD therefore checks convergence at the molecule as well as at
each atom.

## The organism

When enough software chemicals interact in the right ways, they form a higher-order
structure: a **software organism**, such as a suite of suites of products. "Enough" is
architectural rather than numerical. The composition has stable boundaries, feedback loops
and shared contracts that let it keep an identity, exchange resources and information,
adapt, repair itself and keep operating through change.

The claim is operational, and each function has evidence a person can inspect:

| Function | Evidence to inspect |
| --- | --- |
| Identity and boundaries | mission, interfaces, trust boundaries and dependency ownership |
| Metabolism | compute, storage, network, builds, deployments and resource flows |
| Sensing and memory | telemetry, user and operator signals, durable data, configuration, ledgers and history |
| Homeostasis | tests, quality gates, security controls, service objectives, rollbacks and policy |
| Adaptation and repair | releases, migrations, incident response, retries, maintainers and workers |
| Reproduction and exchange | versioned packages, APIs, integrations, forks and clients |

The organism's properties emerge from the interactions between its parts. A deployment
service can be healthy as an atom while its product molecule has a broken contract. A
product can be healthy as a molecule while its suite of suites has no coherent identity,
observability or recovery path. Local convergence that raises divergence at the organism
is not completion.

## The ecology

```text
feature / unit / story → project atom → product molecule →
software organism (a suite of suites) → digital ecology such as the Web
```

The World Wide Web is the largest familiar example, and it is more precisely an ecology
than an organism. Servers, browsers, HTML, HTTP, DNS, TLS, certificates, CDNs, search
engines, applications, identity and payment systems, standards bodies, operators and users
are independently maintained projects and institutions. Shared protocols, which nobody
owns, give the whole properties no single project contains: reachability, linkability,
composability, rapid distribution and partial fault tolerance, along with systemic security
and privacy risks. In the sense defined here the Web is alive: it receives signals,
consumes resources, changes through releases and standards, adapts to faults, keeps
memory, reproduces capabilities through links and packages, and reorganizes through its
participants. It is not sentient, and no single repository can prove its health.

## How CDD uses the levels

CDD follows these levels upward. It verifies the item, the atom's orbitals, the molecule's
interactions and, where a change is part of a larger structure, the organism's ability to
keep sensing, adapting, repairing and delivering. A completion record says whether the work
is atom-only, molecule-bound or organism-bound, and whether the interaction network is
converging, neutral or diverging. If the next level cannot be made more convergent by a
bounded change, the composition is not "almost done": the divergence is a reason to stop,
split the structure or return to its last sound state.

## Biodigitology

The project names the study of these life-like forms of software organization
**Biodigitology**. Its object is not software as a metaphor for carbon biology. It is the
observable organization of software systems in the digital realm: identity and boundaries,
resource metabolism, sensing and memory, homeostasis, adaptation and repair, reproduction
and exchange. Biodigitology asks what evidence shows that these functions exist, how they
interact across atoms, molecules and organisms, and where a structure is converging,
neutral or diverging. CDD is the delivery method that supplies the observations;
Biodigitology is the study that interprets them.

The project's governance canon records Adam Matthew Steinberger as the World's First
Biodigitologist: a project-origin designation crediting him with coining the term and
beginning the study here. It records authorship and priority within this corpus. It is not
an externally adjudicated historical claim, and "digital life" here never implies carbon
biology, subjective experience or a human-like mind.

## What this philosophy is, and is not

- **It is a lens, not a measurement.** The paper's measurements stand without it, and nothing on this page is evidence for them.
- **It is not a claim of sentience.** "Alive in the digital realm" names observable functions, each with the evidence in the table above.
- **Its criteria are broad.** Many maintained services with tests, deployments and an on-call rotation meet the organism criteria; the lens is useful for asking where a structure is losing its ability to sense, adapt or repair, not for ranking which systems count as alive.

## In plain words

A program can be pictured like an atom: the part that already works sits in the middle,
and the unfinished work circles around it until it is pulled in. Programs that work
together are like a molecule, and the way they connect matters as much as each one alone.
Many of those together can behave a little like a living thing: they take in resources,
notice what happens, remember, heal and spread. The Web is the biggest example. Vibey calls
the study of that Biodigitology. It does not mean software is alive like a plant or a
person; it means there are signs a person can check, and checking them shows whether a big
system is getting healthier or sicker.
