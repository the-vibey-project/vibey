---
id: skill-11-applications-eb3cf9f7fe
purpose: 11 applications
source: src/vibey_tools/skills/plugins/quantum-computing/skills/quantum-applications-and-post-quantum-crypto/SKILL.md
requires: []
links: ["skill-12-quantum-networking-and-sensing-dce2c7ef2e"]
---

## §11. Applications

### 11.1 Quantum chemistry and materials — the strongest case

**[DURABLE]** Simulating molecules and materials is the application where the exponential
advantage is least disputed, because the problem *is* a quantum system. Targets: catalysis
(nitrogen fixation is the canonical example), battery chemistry, superconductors, drug
binding affinities. **Near-term**: VQE on small molecules (⚠️ heuristic, barren plateaus,
§4.4 → `quantum-noise-error-correction-and-hardware`). **Fault-tolerant**: quantum phase estimation on industrially relevant systems —
which requires §5 → `quantum-noise-error-correction-and-hardware`-scale hardware.

**⚠️ Reality check**: classical computational chemistry (DFT, coupled cluster, DMRG,
quantum Monte Carlo) is very good and improving, and the quantum-advantage crossover point
for industrially relevant molecules is genuinely uncertain.

### 11.2 Optimization

Portfolio optimization, routing, scheduling, supply chain — the most-marketed application
and the **weakest technical case**. QAOA and quantum annealing are heuristics with no proven
advantage, and **classical solvers (Gurobi, CPLEX, specialized heuristics, and simulated
annealing) frequently match or beat quantum approaches** on the same problems. **[CONTESTED]
§16.4 → `quantum-reference`.**

### 11.3 Quantum machine learning

**⚠️ The most oversold area.** Two structural problems: **the data-loading bottleneck** —
there is no efficient way to load a large classical dataset into a quantum state, and QRAM
remains theoretical — and **dequantization** (§10.3 → `quantum-software-and-resource-estimation`), which removed the claimed speedup from
a whole family of QML algorithms. Add barren plateaus (§4.4 → `quantum-noise-error-correction-and-hardware`) and the result that **provable
absence of barren plateaus may imply classical simulability**, and the honest position is
that QML's advantage case is currently weak. **The plausible exception: machine learning on
data that is *natively quantum*** (from quantum sensors or quantum simulations), where the
loading problem doesn't arise.

### 11.4 Finance, and everything else

Derivative pricing via amplitude estimation (quadratic — see §9.3 → `quantum-software-and-resource-estimation` for why that may not
survive), risk analysis, fraud detection. Real bank R&D programs exist; **no production
quantum advantage has been demonstrated in finance.** The reasonable framing for enterprises
is capability-building and option value, not near-term ROI.

---
