---
id: skill-11-hamiltonian-chaos-and-kam-9923a346cc
purpose: 11 hamiltonian chaos and kam
source: src/vibey_tools/skills/plugins/chaos-theory/skills/chaos-fractals-poincare-and-hamiltonian-chaos/SKILL.md
requires: ["skill-10-poincar-sections-and-symbolic-dynamics-0e3fe813d5"]
links: []
---

## §11. Hamiltonian Chaos and KAM

**⚠️ Conservative systems are different from dissipative ones and the distinction is
fundamental**: **Liouville's theorem means phase space volume is preserved**, so
⚠️ **there are no attractors at all.** **`Σλᵢ = 0`**, and exponents come in `±` pairs.

**Integrable systems** have as many conserved quantities as degrees of freedom; ⚠️ **motion
is confined to invariant tori and is quasi-periodic.** **These are the textbook systems —
and they are measure-zero exceptional.**

**⚠️ KAM theorem (Kolmogorov-Arnold-Moser)** — under a **small** perturbation of an
integrable system, **most invariant tori survive, slightly deformed.** ⚠️ **Tori with
sufficiently irrational frequency ratios are the most robust; resonant tori break up
first**, and the destroyed ones are replaced by **chaotic layers.**
**⚠️ The resulting picture is mixed phase space**: islands of regular motion embedded in a
chaotic sea, **at every scale.** **This is the generic situation, and it means "is this
system chaotic?" can have the answer "it depends where you start."**

**Arnold diffusion** — ⚠️ **for 3+ degrees of freedom, chaotic regions connect and slow
transport through phase space becomes possible.**
**Standard (Chirikov) map** — the canonical model. **Chirikov's resonance-overlap
criterion** gives a practical estimate of when chaos sets in.

**⚠️ Practical consequences**: **solar system stability is a KAM question and is not
settled** — Mercury's orbit is chaotic with a Lyapunov time of a few million years;
**asteroid belt Kirkwood gaps are resonance-driven chaos**; and **particle accelerator
beam dynamics is Hamiltonian chaos with real budgets attached.**
