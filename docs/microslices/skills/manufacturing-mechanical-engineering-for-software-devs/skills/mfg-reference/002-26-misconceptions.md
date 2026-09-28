---
id: skill-26-misconceptions-fac101d625
purpose: 26 misconceptions
source: src/vibey_tools/skills/plugins/manufacturing-mechanical-engineering-for-software-devs/skills/mfg-reference/SKILL.md
requires: ["skill-25-what-s-live-verified-august-2026-1917266cea"]
links: ["skill-27-numbers-48426d6cf8"]
---

## §26. Misconceptions

| Misconception | Correction |
|---|---|
| Stiffness and strength are the same | ⚠️ **Steel and stainless share E; strengths differ hugely** (§2 → `mfg-mechanics-stress-fatigue-and-materials`) |
| Parts fail when overloaded | ⚠️ **Fatigue kills below yield, after cycles** (§4 → `mfg-mechanics-stress-fatigue-and-materials`) |
| Aluminium has an endurance limit | ⚠️ **It doesn't. It accumulates damage at any amplitude** (§4 → `mfg-mechanics-stress-fatigue-and-materials`) |
| Sharp corners are fine | ⚠️ **Stress concentration. Add a radius** (§2 → `mfg-mechanics-stress-fatigue-and-materials`, §4 → `mfg-mechanics-stress-fatigue-and-materials`) |
| More bolts and pins make it stronger | ⚠️ **Over-constraint makes parts fight each other** (§7 → `mfg-machine-elements-mechanisms-and-tolerances`) |
| Lock washers prevent loosening | ⚠️ **Split lock washers are largely ineffective** (§6 → `mfg-machine-elements-mechanisms-and-tolerances`) |
| Tighter tolerances are better engineering | ⚠️ **They cost non-linearly. Tolerance the FUNCTION** (§8 → `mfg-machine-elements-mechanisms-and-tolerances`) |
| Worst-case stack-up is the right method | ⚠️ **Often absurdly conservative; RSS is realistic** (§8 → `mfg-machine-elements-mechanisms-and-tolerances`) |
| A dimension is a number | ⚠️ **It's a distribution. GD&T states intent** (§8 → `mfg-machine-elements-mechanisms-and-tolerances`) |
| CAD geometry can be made | ⚠️ **Round cutters can't make sharp internal corners** (§11 → `mfg-process-families-machining-additive-and-moulding`) |
| 3D printing will replace manufacturing | ⚠️ **It loses badly at volume** (§13 → `mfg-process-families-machining-additive-and-moulding`, §25.1) |
| Casting and forging are interchangeable | ⚠️ **Forging's grain flow gives better fatigue life** (§10 → `mfg-process-families-machining-additive-and-moulding`) |
| Thick walls are stronger | ⚠️ **They sink in moulding and cast porous** (§10 → `mfg-process-families-machining-additive-and-moulding`, §14 → `mfg-process-families-machining-additive-and-moulding`) |
| Welded joints are as strong as the parent | ⚠️ **The heat-affected zone is where it fails** (§12 → `mfg-process-families-machining-additive-and-moulding`) |
| Adhesives are weak | ⚠️ **Strong in shear, poor in peel. Design the joint** (§12 → `mfg-process-families-machining-additive-and-moulding`) |
| FEA results are answers | ⚠️ **Hypotheses. Validate against hand calc and test** (§20 → `mfg-dfm-metrology-plm-npi-and-what-transfers`) |
| Tooling is a detail | ⚠️ **It's the capital cost and the lead time** (§14 → `mfg-process-families-machining-additive-and-moulding`, §19 → `mfg-dfm-metrology-plm-npi-and-what-transfers`) |
| A revision is like a git commit | ⚠️ **Non-interchangeable means a NEW part number** (§21 → `mfg-dfm-metrology-plm-npi-and-what-transfers`) |
| You can roll back a change | ⚠️ **Old revisions physically exist, for decades** (§21 → `mfg-dfm-metrology-plm-npi-and-what-transfers`) |
| Just order a few for testing | ⚠️ **Setup and MOQ dominate at low volume** (§19 → `mfg-dfm-metrology-plm-npi-and-what-transfers`) |
| Inspection ensures quality | ⚠️ **Capable processes do. Also check gauge R&R** (§18 → `mfg-dfm-metrology-plm-npi-and-what-transfers`) |
| Robots are replacing manufacturing labour | ⚠️ **The driver is unfilled vacancies** (§25.2) |
| Humanoids are about to transform factories | ⚠️ **The IFR lists the unmet requirements plainly** (§25.2) |
| Mechanical engineers are just conservative | ⚠️ **Change costs six figures. It's rational** (§1 → `mfg-mechanics-stress-fatigue-and-materials`, §24 → `mfg-dfm-metrology-plm-npi-and-what-transfers`) |

---
