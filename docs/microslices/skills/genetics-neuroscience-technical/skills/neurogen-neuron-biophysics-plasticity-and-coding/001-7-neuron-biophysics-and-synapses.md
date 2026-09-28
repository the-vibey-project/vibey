---
id: skill-7-neuron-biophysics-and-synapses-a3bccd6f39
purpose: 7 neuron biophysics and synapses
source: src/vibey_tools/skills/plugins/genetics-neuroscience-technical/skills/neurogen-neuron-biophysics-plasticity-and-coding/SKILL.md
requires: []
links: ["skill-8-plasticity-f49ae19a33"]
---

## §7. Neuron Biophysics and Synapses

**[Hodgkin–Huxley, Nernst, and cable theory are derived in a biomedical-engineering
reference §9. Here: what they imply.]**

**Resting potential ≈ −70 mV**, set by K⁺ permeability and the Na⁺/K⁺-ATPase
(⚠️ **3 Na⁺ out : 2 K⁺ in — electrogenic, and it consumes a large share of the brain's
ATP**). **Action potential**: threshold ~−55 mV → Na⁺ influx (regenerative) → K⁺ efflux →
afterhyperpolarization. **Refractory period** enforces directionality and caps firing rate.

**Cable equation** for dendritic propagation:
```
λ = √(r_m/r_i)          ⚠️ length constant — how far a signal decays passively (0.1–1 mm)
τ_m = r_m·c_m           membrane time constant (~10–20 ms)
```
**⚠️ Passive decay is why dendrites need active conductances**; dendritic Na⁺ and Ca²⁺
channels support local spikes, making **the dendrite a computational unit, not a passive
cable** — individual branches can act as independent nonlinear subunits.

**Myelination and saltatory conduction**: ⚠️ **conduction velocity scales roughly linearly
with diameter in myelinated axons (~6 × diameter in µm m/s) but only as √diameter
unmyelinated** — which is why myelin is such an efficient solution.

**Synaptic transmission**: AP → **Ca²⁺ influx through voltage-gated channels** →
⚠️ **vesicle fusion is steeply Ca²⁺-dependent (roughly 4th power), which makes release
probabilistic and highly modulable** → neurotransmitter → receptor.

| Receptor | Type | Effect |
|---|---|---|
| **AMPA** | ionotropic glutamate | Fast excitatory, Na⁺/K⁺ |
| **NMDA** | ionotropic glutamate | ⚠️ **Mg²⁺ block relieved by depolarization + needs glutamate → a COINCIDENCE DETECTOR. Ca²⁺-permeable. This is the molecular basis of §8** |
| **Kainate** | ionotropic glutamate | Modulatory |
| **mGluR** | metabotropic | Slow modulation |
| **GABA_A** | ionotropic | ⚠️ **Fast inhibition via Cl⁻ — and the benzodiazepine/barbiturate target** |
| **GABA_B** | metabotropic | Slow inhibition, K⁺ |
| **Glycine** | ionotropic | Inhibition, spinal cord and brainstem |
| **nACh / mACh** | ionotropic / metabotropic | §11 → `neurogen-circuits-neuromodulation-and-neural-engineering` |

**⚠️ GABA is not always inhibitory.** Its effect depends on the **chloride reversal
potential**, which is set by the KCC2/NKCC1 transporter ratio. **In immature neurons GABA
is depolarizing**, and KCC2 downregulation in injury or epilepsy can make it depolarizing
again in adults — a real mechanism, not a curiosity.

**Short-term plasticity**: **facilitation** (residual Ca²⁺) and **depression** (vesicle
depletion). ⚠️ **A synapse is a dynamic filter — depressing synapses act as high-pass /
change detectors, facilitating ones as low-pass integrators.**

---
