---
id: skill-5-error-correction-and-fault-tolerance-bbd626470d
purpose: 5 error correction and fault tolerance
source: src/vibey_tools/skills/plugins/quantum-computing/skills/quantum-noise-error-correction-and-hardware/SKILL.md
requires: ["skill-4-noise-and-the-nisq-era-69c489f1e4"]
links: ["skill-6-hardware-modalities-a4ab1862ef"]
---

## §5. Error Correction and Fault Tolerance

### 5.1 The idea

**[DURABLE]** No-cloning forbids naive redundancy, but you can encode one **logical qubit**
into many **physical qubits** and measure *stabilizers* — operators that reveal error
syndromes **without measuring (and collapsing) the logical state**. Then correct.

**The threshold theorem [DURABLE, and it's why the field exists]:** if physical error rates
are below a threshold, arbitrarily long computations become possible with polylogarithmic
overhead. The surface-code threshold is around **~1%**, which is why the field spent two
decades pushing gate fidelities toward it.

### 5.2 Codes

| Code | Overhead | Notes |
|---|---|---|
| **Surface code** | High (~1000:1 for useful rates) | 2D nearest-neighbour connectivity, high threshold. **The default for superconducting** |
| **Color codes** | Similar | Transversal gates are easier; lower threshold |
| **qLDPC codes** | **Much lower** | Requires long-range connectivity. **The most important recent development** — the main hope for reducing overhead |
| **Bosonic codes** (cat, GKP) | Different trade-off | Encode in an oscillator's infinite-dimensional space; hardware-efficient |
| **Concatenated codes** | Historically first | Simple analysis, worse thresholds |

### 5.3 The 2024–2026 breakthrough

**[VERSIONED — this is what actually changed.]** **Google's Willow chip (105
superconducting qubits, announced 9 December 2024) demonstrated "below threshold" error
correction for the first time on real hardware**: running the surface code at **distance
3, 5, and 7 on the same chip**, the logical error rate fell **monotonically — roughly
halving with each increase in code distance**.

**Why that specific result mattered [DURABLE reasoning]:** before Willow, nobody had
publicly demonstrated that *adding more physical qubits actually lowered the logical error
rate*. Every prior scaling attempt had added more error than it corrected. Willow
eliminated the legitimate scientific objection that scalable error correction might be
physically impossible on superconducting hardware.

**⚠️ What it did not do:** demonstrate fault tolerance at useful scale. **A distance-7
surface code uses 49 physical qubits to produce one logical qubit**; Shor's on RSA-2048
requires millions of them. **The pathway is now credible. The pathway is still long.**

### 5.4 Magic states — the hidden cost

**[DURABLE]** Clifford gates can be done transversally and cheaply; **T gates cannot**.
The standard solution is **magic state distillation**: consume many noisy states to produce
one clean `|T⟩`. **This dominates the resource cost of fault-tolerant algorithms** — often
the majority of the qubits and time in a resource estimate (§9 → `quantum-software-and-resource-estimation`). Reducing or eliminating
distillation overhead (transversal T gates, better codes) is one of the two remaining
engineering problems, alongside raw physical qubit scaling.

---
