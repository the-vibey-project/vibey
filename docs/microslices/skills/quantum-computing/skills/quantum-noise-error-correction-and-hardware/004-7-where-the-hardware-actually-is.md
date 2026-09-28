---
id: skill-7-where-the-hardware-actually-is-ab62833892
purpose: 7 where the hardware actually is
source: src/vibey_tools/skills/plugins/quantum-computing/skills/quantum-noise-error-correction-and-hardware/SKILL.md
requires: ["skill-6-hardware-modalities-a4ab1862ef"]
links: []
---

## §7. Where the Hardware Actually Is

**[VERSIONED — highest decay risk in this document. Verify everything here.]**

### 7.1 The roadmaps

**IBM** publishes the most specific named-deliverable roadmap in the industry:
- **Nighthawk** — 120-qubit processor with 218 next-generation tunable couplers in a square
  lattice; ~30% more circuit complexity than the Heron family. Targeted to run
  **~7,500 gates in 2026** with up to three 120-qubit modules (360 qubits), **10,000 gates
  in 2027**, **15,000 in 2028**.
- **Loon** — debuted 2025 with c-couplers linking qubits across the chip, the architecture
  needed for qLDPC codes.
- **Kookaburra** — the first module built around modular Quantum System Two, ~4,158 physical
  qubits across the connected cluster; **the first IBM module capable of storing information
  in qLDPC memory and processing it with an attached logical processing unit**.
- **Starling (2029)** — **200 logical qubits from roughly 10,000 physical qubits, running
  100 million operations.** The fault-tolerance target.
- **Blue Jay (2033)** — **2,000 logical qubits, 1 billion operations.**
- IBM states it will **prototype a real-time error-correction decoder in 2026**.

**Google** publishes a six-milestone roadmap. It places itself at **Milestone 2** (~100
physical qubits, logical error rate ~10⁻²) with Willow. Milestone 3 is a long-lived logical
qubit (~10³ physical qubits, 10⁻⁶ logical error). **Milestone 6 is the endpoint: ~10⁶
physical qubits with a 10⁻¹³ logical error rate.** ⚠️ **Google presents the million-qubit
figure as a destination, not a near-term specification** — and the gap from ~100-qubit
chips is enormous.

**Others**: **PsiQuantum** targets a million-qubit utility-scale photonic machine on a
similar horizon. **DARPA's Quantum Benchmarking Initiative** funds Atom Computing,
Photonic Inc., Oxford Ionics (now part of IonQ), and others on parallel fault-tolerance
tracks toward 2033 operational milestones. **Quantinuum** and **Microsoft** have reported
logical-qubit milestones on the H-series trapped-ion systems.

### 7.2 How to read a roadmap

**[DURABLE] Roadmaps are marketing documents with engineering inside them.** The questions
that separate signal from noise:
1. **Physical or logical qubits?** (§0 → `quantum-foundations-and-algorithms` framing 2)
2. **What two-qubit fidelity**, and measured how?
3. **Is the connectivity claim about the chip or about a hypothetical module?**
4. **Has the milestone been demonstrated, or is it a target year?**
5. **Peer-reviewed, preprint, or press release?**
6. **What did the previous roadmap promise for this year, and did it land?** — the single
   most informative question, and the one nobody asks.
