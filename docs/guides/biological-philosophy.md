---
description: The biological lens vibey's development loop is built on, reading software as atoms, molecules, organisms and ecologies, and what it does and does not claim.
---

# Read software as atoms, molecules and organisms: the biological philosophy

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** This page is a lens, not a feature, and you do not need it to
> use vibey. It reads a project as an atom (a proven core with rings of open work), several
> projects as a molecule, and a large suite as an organism with checkable functions such as
> memory and repair. Use it to ask where a large system is losing its ability to sense, adapt or
> repair. It makes no claim that software is conscious. Reading it takes ten minutes.

vibey's development loop, [Convergence-Driven Development](convergence-driven-development.md)
(CDD), measures delivery as a scoreboard: work converges, stays neutral or diverges, and
divergence needs a bounded path back. This page sets out the broader philosophy the project
builds on that scoreboard, and the name it gives the study of it, **Biodigitology**.

The research paper does not rely on this philosophy and does not argue for it: it keeps CDD only
as a scoreboard, in its Discussion, and points here for the rest. The decision behind this page is
[ADR-0041](../architecture/decisions/0041-software-organisms-alive-in-the-digital-realm.md), and
its conduct rule is sub-doctrine 9.d in
[the governance canon](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/docs/doctrines.md).

## The lesson

Daniel arrived with a printout covered in circles and arrows.

**Daniel:** Professor, the docs call a project an atom and the Web a living thing. Is that
science or poetry?

**Professor Feynman:** Neither, quite. It is a way of looking, and a way of looking is only worth
keeping if it helps you notice something. Let us test it. A project has a part that is proven to
work, and a lot of open work around it. Draw the proven part in the middle and the open work as
rings. That is the atom.

**Daniel:** And when the rings are all pulled in?

**Professor Feynman:** Then only the middle is left, and that happens in exactly two cases: the
project is finished, or it is dead. Anything still maintained has rings.

**Daniel:** Fine. And the molecule?

**Professor Feynman:** Two projects that talk to each other. Here is the useful part. Like two
chemicals, the pair has properties neither has alone. Each project can pass all its tests while
the contract between them is broken. So you check the bond, not only the atoms.

**Daniel:** And "alive"? That is the word I don't follow.

**Professor Feynman:** Good, that is where to be careful. It does not mean feeling or thinking. It
means a list of things you can go and look at: does the system know its own boundaries, take in
resources, remember, keep itself in a safe range, repair damage, and spread to new places? If you
can point at evidence for each, the lens calls it alive in the digital realm.

**Daniel:** Then lots of ordinary services are alive.

**Professor Feynman:** Many are, and that is fine. The lens is not for ranking what counts as
alive. It is for asking, of one big system, "which of these functions is getting weaker?" Where
the picture stops working: a real organism has no owner to ask, and every part of this one does.

## Do it: use the lens on a system you run

1. **Draw the atom.** Name what is proven to work, with the evidence, and list the open work at
   four rings: the item, the epic, the milestone, the project.
2. **Find the bonds.** List the other projects it depends on or serves, and for each, the
   interface, the data it owns, and the release timing. Ask whether each bond is converging or
   straining.
3. **Check the six functions** in the table below for the whole structure, and write the evidence
   you can point to beside each one. A blank is a finding.
4. **Report the direction.** Say whether the work is atom-only, bound to a molecule, or bound to an
   organism, and whether the interactions are converging, neutral or diverging. If you cannot say,
   write "unknown".

## Daniel's teach-back

**Daniel:** A project is an atom: a proven middle with rings of open work, and only a finished or
dead project has no rings. Projects that interact are a molecule, and the bonds between them can
break even when each one passes its tests. A large suite can be read as an organism if I can show
evidence for six functions, from knowing its boundaries to repairing itself. It is a way of
asking which functions are weakening, not a claim that software feels anything.

**Professor Feynman:** That is the whole of it. Keep the last sentence closest: it is a lens, and
nothing on this page is evidence for any measurement.

## The atom

- **The nucleus** is the core software already confirmed to work at high quality and to do what it
  is supposed to do.
- **The orbitals** are the four CDD scopes (item, epic, phase, project): living layers of open
  work, pulled toward the nucleus as delivery lowers their unresolved work.

A project with active orbitals is not nucleus-only, even when its nucleus is healthy. Nucleus-only
is a terminal state with exactly two meanings: either the project is complete and needs no
further change, or it is dead and no longer maintained. A maintained project with outstanding
scope or evidence is an atom with active orbitals and keeps running the loop.

## The molecule

Several projects combine their atoms into a software chemical structure: a product, a platform or
a portfolio. As in chemistry, the structure has properties that come from the interactions among
its atoms, not just the sum of their features. Interfaces, dependencies, data ownership, security
boundaries, release timing and operational contracts are the bonds. A bond can lower or raise the
molecule's unresolved work; strain in a bond, such as schema drift, needs a bounded path back to
convergence, or the composition is abandoned. CDD therefore checks convergence at the molecule as
well as at each atom.

## The organism

When enough software chemicals interact in the right ways, they form a higher-order structure: a
**software organism**, such as a suite of suites of products. "Enough" is architectural rather
than numerical. The composition has stable boundaries, feedback loops and shared contracts that
let it keep an identity, exchange resources and information, adapt, repair itself and keep
operating through change.

Each function has evidence a person can inspect:

| Function | Evidence to inspect |
| --- | --- |
| Identity and boundaries | mission, interfaces, trust boundaries and dependency ownership |
| Metabolism | compute, storage, network, builds, deployments and resource flows |
| Sensing and memory | telemetry, user and operator signals, durable data, configuration, ledgers and history |
| Homeostasis | tests, quality gates, security controls, service objectives, rollbacks and policy |
| Adaptation and repair | releases, migrations, incident response, retries, maintainers and workers |
| Reproduction and exchange | versioned packages, APIs, integrations, forks and clients |

The organism's properties emerge from the interactions between its parts. A deployment service can
be healthy as an atom while its product molecule has a broken contract. A product can be healthy
as a molecule while its suite of suites has no coherent identity, observability or recovery path.
Local convergence that raises divergence at the organism is not completion.

## The ecology

```text
feature / unit / story → project atom → product molecule →
software organism (a suite of suites) → digital ecology such as the Web
```

The World Wide Web is the largest familiar example, and it is more precisely an ecology than an
organism. Servers, browsers, HTML, HTTP, DNS, TLS, certificates, CDNs, search engines,
applications, identity and payment systems, standards bodies, operators and users are
independently maintained projects and institutions. Shared protocols, which nobody owns, give the
whole properties no single project contains: reachability, linkability, composability, rapid
distribution and partial fault tolerance, along with systemic security and privacy risks.

Read through this lens, the Web is alive in the digital realm: it receives signals, consumes
resources, changes through releases and standards, adapts to faults, keeps memory, reproduces
capabilities through links and packages, and reorganises through its participants. That is an
interpretation, not a measurement. The Web is not sentient, and no single repository can prove its
health.

## How CDD uses the levels

CDD follows these levels upward. It verifies the item, the atom's orbitals, the molecule's
interactions and, where a change is part of a larger structure, the organism's ability to keep
sensing, adapting, repairing and delivering. A completion record says whether the work is
atom-only, molecule-bound or organism-bound, and whether the interaction network is converging,
neutral or diverging. If the next level cannot be made more convergent by a bounded change, the
composition is not "almost done": the divergence is a reason to stop, split the structure or return
to its last sound state.

The local runner's storm mode asks for this directly: every item's verdict carries a
`composition` field saying whether the item is an atom, part of a chemical structure or part of an
organism (`src/vibey_runners/qwen/src/qwenloop/application/storm.py`).

## Biodigitology

The project names the study of these life-like forms of software organisation **Biodigitology**.
Its object is not software as a metaphor for carbon biology. It is the observable organisation of
software systems in the digital realm: identity and boundaries, resource metabolism, sensing and
memory, homeostasis, adaptation and repair, reproduction and exchange. Biodigitology asks what
evidence shows that these functions exist, how they interact across atoms, molecules and
organisms, and where a structure is converging, neutral or diverging. CDD is the delivery method
that supplies the observations; Biodigitology is the study that interprets them.

The project's governance canon records Adam Matthew Steinberger as the "World's First
Biodigitologist": a project-origin designation crediting him with coining the term and beginning
the study here (sub-doctrine 9.d's terminology note in
[`doctrines.md`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/docs/doctrines.md),
and [`constitution.md`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/docs/constitution.md)).
It records authorship and priority within this corpus only. The canon itself says it is not an
externally adjudicated worldwide priority claim, and no outside body has assessed it.

## What this philosophy is, and is not

- **It is a lens, not a measurement.** The paper's measurements stand without it, and nothing on
  this page is evidence for them.
- **It is not a claim of sentience.** "Alive in the digital realm" names observable functions,
  each with the evidence in the table above. It never implies carbon biology, subjective
  experience or a human-like mind.
- **Its criteria are broad.** Many maintained services with tests, deployments and an on-call
  rotation meet the organism criteria. The lens is useful for asking where a structure is losing
  its ability to sense, adapt or repair, not for ranking which systems count as alive.

## When it goes wrong

| What you notice | What it means | What to do |
|---|---|---|
| Every project passes its tests, but the product does not ship | The molecule is diverging while each atom converges. | Check the bonds: interfaces, data ownership, release timing. |
| A function in the table has no evidence you can point to | The structure may be losing that function, or nobody measures it. | Record it as unknown and decide whether to measure it. |
| Someone cites this page as proof a system is healthy | The lens has been treated as a measurement. | Point to the tests, telemetry and ledgers instead; this page proves nothing. |

## Where next

- [Convergence-Driven Development](convergence-driven-development.md), for the delivery loop this
  lens sits on and its commands.
- [ADR-0041](../architecture/decisions/0041-software-organisms-alive-in-the-digital-realm.md), for
  the decision and its consequences.
- [The research paper](https://the-vibey-project.github.io/vibey/main/paper/), for the measurements
  that do not depend on this page.

## Say it in one line

vibey reads software as atoms, molecules and organisms to ask which checkable functions are
weakening, and is clear that this is a lens, not a claim that software lives or feels.
