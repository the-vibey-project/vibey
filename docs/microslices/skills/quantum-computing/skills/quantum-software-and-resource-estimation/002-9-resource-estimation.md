---
id: skill-9-resource-estimation-70f570ca43
purpose: 9 resource estimation
source: src/vibey_tools/skills/plugins/quantum-computing/skills/quantum-software-and-resource-estimation/SKILL.md
requires: ["skill-8-the-software-stack-f9f382acb5"]
links: ["skill-10-evaluating-quantum-advantage-claims-4efbd999e4"]
---

## §9. Resource Estimation

**[DURABLE] "How many qubits do I need?" is the question that separates serious evaluation
from hype, and the answer is almost always much larger than the headline suggests.**

### 9.1 The chain

```
abstract algorithm
  → gate count and depth (in T gates and Cliffords — count T gates specifically)
    → logical qubit count and logical circuit volume
      → CHOOSE A CODE and a target logical error rate
        → code distance d (set by how long the computation runs)
          → physical qubits per logical qubit (surface code ≈ 2d² per logical qubit)
            → + MAGIC STATE FACTORIES (often the majority of the footprint, §5.4)
              → total physical qubits, and wall-clock runtime
```

### 9.2 The canonical example: breaking RSA-2048

**[DURABLE as a structure; the specific numbers are [VERSIONED] and have fallen
substantially over the last decade as the algorithms improved.]** Published estimates have
ranged from roughly **20 million noisy physical qubits over ~8 hours** (Gidney–Ekerå 2019,
the most-cited figure) downward as factoring circuits and codes have improved. Current
hardware is in the **hundreds** of physical qubits.

**⚠️ Do not quote a single number as settled.** The estimates depend on assumed physical
error rate, code choice, cycle time, and the specific factoring circuit — and they have
been revised downward repeatedly. **The direction of travel matters more than any point
estimate**, and it is downward.

### 9.3 Why quadratic speedups often evaporate

**[DURABLE, and this is the most under-appreciated result in practical quantum computing.]**
Grover-type quadratic speedups must overcome:
- **Error-correction overhead** — every logical operation costs many physical ones.
- **Slow logical clock rates** — a logical gate takes many physical cycles (microseconds to
  milliseconds effective).
- **No parallelism advantage** — you can't parallelize Grover the way you parallelize a
  classical search across a datacenter.

The consequence: **for many realistic problem sizes, a classical cluster beats a
fault-tolerant quantum computer running a quadratically-faster algorithm.** Quadratic
speedups need enormous problem instances before they pay. **Exponential speedups are the
ones that survive the overhead**, which is why §3 → `quantum-foundations-and-algorithms`'s split between proven-exponential and
heuristic matters so much commercially.

---
