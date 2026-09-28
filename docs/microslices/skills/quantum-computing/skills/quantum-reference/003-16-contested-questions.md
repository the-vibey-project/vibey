---
id: skill-16-contested-questions-ce782b808c
purpose: 16 contested questions
source: src/vibey_tools/skills/plugins/quantum-computing/skills/quantum-reference/SKILL.md
requires: ["skill-15-myths-and-anti-patterns-4afb01dfd9"]
links: ["skill-17-currency-snapshot-verified-august-2026-e0ebc6b3b2"]
---

## §16. Contested Questions

**16.1 When does a cryptographically-relevant quantum computer arrive?** Expert estimates
cluster around **2030–2035** with enormous error bars, and the security-community central
estimate has been roughly **2033–2035**. **[VERSIONED, and important]: NCSC, NSA, and NIST
did not revise that estimate upward in response to Willow, Nighthawk, or Majorana 1, and
no standards body changed its deprecation schedule as a direct result.** What changed was
**the credibility of the estimate**, not the date: Willow removed the "maybe error
correction is physically impossible" objection, and four architecturally distinct programmes
hitting milestones simultaneously reduces the risk that one technical obstacle blocks the
whole field. **Note the asymmetry in the decision: you must migrate on the pessimistic
timeline regardless (§13.1 → `quantum-applications-and-post-quantum-crypto`).**

**16.2 Has quantum advantage been achieved?** §10.4 → `quantum-software-and-resource-estimation`. The 2026 position is roughly:
*probably yes on contrived tasks*, with the live argument being whether usefulness and
verifiability should be requirements for the term. Skepticism persists because benchmark
tasks are contrived, verification relies on indirect proxies, and early experiments were
partially matched by later classical simulation.

**16.3 Is NISQ a dead end?** *For NISQ*: real hardware today, learning value, possible
niche wins, and it builds the engineering base for fault tolerance. *Against*: **no proven
advantage from any NISQ algorithm**, barren plateaus, mitigation costs that scale
exponentially, and the result that provably-trainable circuits may be classically
simulable. **A growing view is that useful quantum computing requires fault tolerance, full
stop, and NISQ was an interesting detour.** Held seriously by serious people on both sides.

**16.4 Quantum annealing and optimization.** D-Wave has thousands of qubits and real
commercial deployments; it is also **not a universal quantum computer**, and its claimed
advantages have been repeatedly matched by classical methods. **[CONTESTED]** whether
annealing offers any asymptotic advantage at all.

**16.5 Topological qubits.** Microsoft's Majorana-based approach promises error protection
built into the physics. **It is the most scientifically contested modality** — a
high-profile Majorana paper was retracted in 2021, and subsequent claims have drawn
substantial expert skepticism. **Genuinely unresolved.**

**16.6 Is the field overinvested?** *For the bubble case*: no commercial advantage yet,
valuations disconnected from revenue, repeated timeline slippage, and dequantization
history. *Against*: the physics is proven, error correction crossed a real threshold in
2024–2026, the cryptographic threat alone justifies national investment, and the downside
of being late is severe. **[VERSIONED]** The US **EO 14413 (June 2026)** established a
national effort toward a science-enabling quantum computer, directed an update to the
National Quantum Strategy, and mandated domestic quantum workforce institutes and supply
chain strategies — so the state-level bet is being *increased*, whatever one thinks of the
private valuations.

**16.7 Should my organization do anything now?** **The clear answer for PQC is yes,
immediately** (§13 → `quantum-applications-and-post-quantum-crypto`) — that's regulatory and HNDL-driven, not hardware-driven. For quantum
*computing*, the honest answer for most organizations is **education and monitoring, not
deployment**: build literacy (which takes years), identify whether you have genuinely
quantum-suited problems (optimization, simulation, and sampling with real structural
bottlenecks), and avoid pilots whose main output is a press release.

---
