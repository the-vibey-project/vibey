---
id: skill-8-the-software-stack-f9f382acb5
purpose: 8 the software stack
source: src/vibey_tools/skills/plugins/quantum-computing/skills/quantum-software-and-resource-estimation/SKILL.md
requires: []
links: ["skill-9-resource-estimation-70f570ca43"]
---

## §8. The Software Stack

### 8.1 The layers

```
Application / domain library   (chemistry, finance, optimization)
  ↓
Algorithm / modeling layer     (Qmod, high-level synthesis)
  ↓
High-level SDK                 (Qiskit, Cirq, PennyLane, Q#, CUDA-Q)  ← most people live here
  ↓
Compilation / transpilation    (Qiskit transpiler, PyTKET) — routing, gate synthesis,
                                optimization, error-mitigation insertion
  ↓
Instruction-set language       (OpenQASM 3, Quil)
  ↓
Pulse-level control            (microsecond-timescale hardware control)
  ↓
Physical hardware
```

### 8.2 The frameworks

| Framework | Owner | Best at |
|---|---|---|
| **Qiskit** | IBM | The most feature-rich and most-taught. Circuits, noise modeling, dynamic circuits, native OpenQASM 3. **Start here if you want the biggest tutorial ecosystem** |
| **Cirq** | Google-affiliated | More explicit about hardware; rewards wanting to understand what the device does |
| **PennyLane** | Xanadu | **Quantum machine learning and autodiff.** Integrates with JAX, PyTorch, TensorFlow; broad plugin support across hardware |
| **CUDA-Q** | NVIDIA | Hybrid quantum-classical across GPUs, CPUs, and QPUs. The HPC-integration play |
| **Q#** | Microsoft | A dedicated language; teaches algorithm structure cleanly |
| **Braket** | AWS | Managed multi-vendor cloud access |
| **PyTKET** | Quantinuum | Compilation and optimization; often the best transpiler |
| **Ocean** | D-Wave | Annealing / QUBO |
| **Stim**, **Mitiq**, **Qualtran** | Community | Stabilizer simulation (fast QEC simulation), error mitigation, resource estimation |

**[DURABLE] Transpilation is where the practical difficulty lives.** Your abstract circuit
must be mapped onto real hardware with limited connectivity — inserting SWAP networks,
decomposing into native gates, and optimizing depth. **On a nearest-neighbour device, SWAP
insertion can multiply your gate count several-fold**, and this is invisible in the code
you wrote. Always look at the transpiled circuit, not the one you authored.

### 8.3 What programming quantum computers is actually like

**[DURABLE] Closer to embedded systems or FPGA design than to normal software
engineering**: severe resource constraints (tens to a few hundred qubits, strict depth
limits before errors dominate), no debugger in any conventional sense (measurement destroys
the state), **statistical rather than deterministic validation** (you check error rates,
not outputs), and algorithms usually verified mathematically *before* they're tested.

Practical workflow: **write it, simulate it small (≤~30 qubits on a laptop, ~40–50 on a
cluster), verify against a classical reference, then run on hardware and expect it to look
worse.** Simulators are where nearly all learning happens.

---
