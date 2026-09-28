---
id: skill-8-plasticity-f49ae19a33
purpose: 8 plasticity
source: src/vibey_tools/skills/plugins/genetics-neuroscience-technical/skills/neurogen-neuron-biophysics-plasticity-and-coding/SKILL.md
requires: ["skill-7-neuron-biophysics-and-synapses-a3bccd6f39"]
links: ["skill-9-neural-coding-dfa2e30272"]
---

## §8. Plasticity

**Hebb**: cells that fire together wire together. Formalized:
```
Δw_ij = η · x_i · y_j          ⚠️ unstable — weights grow without bound
```
**Stabilizations**: **Oja's rule** (normalization, and ⚠️ **it converges to the first
principal component — Hebbian learning is PCA**), **BCM** (⚠️ **sliding threshold θ_M
that adapts to recent activity, giving both LTP and LTD**), **synaptic scaling**
(homeostatic, multiplicative, ⚠️ **preserves relative weights while stabilizing total
drive**).

**LTP/LTD mechanism**: **NMDA receptor coincidence detection** (§7) → Ca²⁺ influx →
⚠️ **high Ca²⁺ → CaMKII → AMPA receptor insertion → LTP; modest Ca²⁺ → calcineurin/PP1 →
AMPA removal → LTD.** **The amplitude of the calcium transient is the sign of the
plasticity** — one mechanism, two directions.

**⚠️ STDP** — the timing rule:
```
pre before post (~+10 ms)   → potentiation
post before pre (~−10 ms)   → depression
Window ~±20–50 ms, asymmetric and exponentially decaying
```
**⚠️ STDP is a real phenomenon, not a universal law**: the window shape varies by synapse
type, brain region, and dendritic location, and **it depends strongly on firing rate and
on neuromodulatory state** — which is the bridge to §11 → `neurogen-circuits-neuromodulation-and-neural-engineering`.

**Three-factor rules** — ⚠️ **pre × post × neuromodulator.** This is how a global reward or
novelty signal gates which coincidences get consolidated, and it is the most plausible
biological answer to the credit-assignment problem.

**Structural plasticity**: spine formation and elimination, ⚠️ **and consolidation requires
protein synthesis — which is why late-LTP is blocked by translation inhibitors and early
LTP isn't.** **Synaptic tagging and capture** explains how weakly-stimulated synapses can
capture plasticity-related proteins made elsewhere.

---
