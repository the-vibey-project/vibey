---
id: skill-14-admet-prediction-ac76d820b0
purpose: 14 admet prediction
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-qsar-admet-generative-models-and-validation/SKILL.md
requires: ["skill-13-qsar-and-property-prediction-bb75f51752"]
links: ["skill-15-generative-models-52158818bf"]
---

## §14. ADMET Prediction

```
ABSORPTION  solubility, permeability (Caco-2, PAMPA), efflux (P-gp)
DISTRIBUTION  plasma protein binding, ⚠️ blood-brain barrier, volume
METABOLISM  ⚠️ CYP450 inhibition and substrate; metabolic stability;
   ⚠️ SITE OF METABOLISM prediction
EXCRETION  clearance, half-life
⚠️ TOXICITY  ⚠️ hERG (cardiac liability — the classic killer),
   hepatotoxicity, Ames mutagenicity, reactive metabolites
```
**⚠️ ADMET models are among the most USEFUL in practice** — ⚠️ **because the endpoints are
measured consistently in-house, the datasets are large, and early filtering has genuine
value.** **⚠️ hERG and CYP models in particular are standard.**
**⚠️ The caution**: ⚠️ **in vitro endpoints are proxies for in vivo behaviour, and in vivo
is a proxy for human.** **⚠️ Each step loses information, which is why physiologically-based
pharmacokinetic (PBPK) modelling exists to bridge them** — **and PBPK is itself an area
where regulators accept computational evidence** (§24.2 → `drugdev-reference`).

---
