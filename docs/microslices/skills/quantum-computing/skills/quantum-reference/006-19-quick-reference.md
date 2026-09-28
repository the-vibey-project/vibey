---
id: skill-19-quick-reference-31f48abeba
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/quantum-computing/skills/quantum-reference/SKILL.md
requires: ["skill-18-the-canon-d4393d5958"]
links: ["skill-20-sources-and-method-bf462cdfbe"]
---

## §19. Quick Reference

### 19.1 Numbers
- **n qubits → 2ⁿ amplitudes**, but **n classical bits out per measurement.**
- Surface code: **~2d² physical qubits per logical qubit**; **d=7 → 49 physical per logical.**
- Surface code threshold: **~1%** physical error rate.
- Current two-qubit gate errors: **~10⁻³–10⁻²**; single-qubit **~10⁻⁴–10⁻³**.
- **T2 ≤ 2·T1**, always.
- Classical simulation limit: **~30 qubits on a laptop, ~40–50 on a cluster.**
- RSA-2048: **millions of physical qubits** (estimates ~20M and falling).
- **IBM Starling 2029: 200 logical / ~10,000 physical / 100M operations.**
- **Google Milestone 6: ~10⁶ physical qubits.**
- PQC: **RSA/ECC deprecated after 2030, disallowed after 2035.**
- Enterprise PQC migration: **42–54 months.**

### 19.2 Evaluating any quantum claim
- [ ] Physical or logical qubits?
- [ ] Two-qubit gate fidelity, measured how?
- [ ] Is the task useful, or constructed for the demo?
- [ ] Is the result verifiable, and by what method?
- [ ] Compared against the **best** classical approach, or a convenient one?
- [ ] Peer-reviewed, preprint, or press release?
- [ ] Has 6–18 months passed for classical researchers to respond?
- [ ] Does the previous roadmap's promise for this year look accurate in hindsight?
- [ ] Proven speedup, or heuristic?
- [ ] If quadratic — does it survive error-correction overhead (§9.3 → `quantum-software-and-resource-estimation`)?

### 19.3 What to actually do
| If you are... | Do |
|---|---|
| Any organization | **Start PQC migration now** — inventory first (§13.4 → `quantum-applications-and-post-quantum-crypto`). This is regulatory and HNDL-driven |
| A US federal agency or contractor | Check **EO 14412 / OMB M-26-15** obligations and the **FAR** implications immediately |
| Evaluating a quantum vendor pilot | Run §19.2 on everything they show you; ask what the previous roadmap promised |
| Curious and technical | Linear algebra → Qiskit textbook → simulator. Skip the analogies (§14) |
| Looking for real quantum problems | **Simulation of quantum systems** is the defensible case (§11.1 → `quantum-applications-and-post-quantum-crypto`). Optimization and ML are not |
| In a domain with 10+ year data confidentiality | You are **already exposed** to HNDL (§13.1 → `quantum-applications-and-post-quantum-crypto`) |

---
