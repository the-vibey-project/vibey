---
id: skill-6-hardware-modalities-a4ab1862ef
purpose: 6 hardware modalities
source: src/vibey_tools/skills/plugins/quantum-computing/skills/quantum-noise-error-correction-and-hardware/SKILL.md
requires: ["skill-5-error-correction-and-fault-tolerance-bbd626470d"]
links: ["skill-7-where-the-hardware-actually-is-ab62833892"]
---

## §6. Hardware Modalities

**[DURABLE] No modality has won, and each fails differently.** The trade-off structure is
stable even as the numbers move.

| Modality | Players | Strengths | Weaknesses |
|---|---|---|---|
| **Superconducting** | IBM, Google, Rigetti, IQM | Fast gates (ns), fab-compatible, most mature | Short coherence (µs), millikelvin dilution fridges, nearest-neighbour connectivity, crosstalk |
| **Trapped ion** | Quantinuum, IonQ | **Best gate fidelities**, all-to-all connectivity, identical qubits, long coherence | **Slow gates (µs–ms)**, scaling requires shuttling or photonic interconnects |
| **Neutral atom** | QuEra, Pasqal, Atom Computing | **Massive qubit counts** (1000+ demonstrated), reconfigurable geometry, room-temperature-ish optics | Slower operations, atom loss, younger |
| **Photonic** | PsiQuantum, Xanadu | Room temperature, natural networking, fast | Probabilistic gates, photon loss, needs enormous component counts |
| **Spin / silicon** | Intel, Diraq, academic | CMOS-compatible, tiny footprint, potential to leverage existing fabs | Least mature; variability between devices |
| **Topological** | Microsoft | Error protection built into the physics | ⚠️ **Most scientifically contested** (§16.5 → `quantum-reference`) |
| **Annealing** | D-Wave | Thousands of qubits *now*, real commercial deployments | **Not universal**; advantage disputed (§16.4 → `quantum-reference`) |

**[DURABLE] The comparison metric that matters is not qubit count.** It's the combination
of **two-qubit gate fidelity**, **connectivity**, **gate speed**, **coherence relative to
gate time**, and **whether the architecture has a credible scaling path**. A vendor quoting
only qubit count is telling you which number flatters them.

---
