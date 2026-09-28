---
id: skill-13-additive-manufacturing-36a35baf34
purpose: 13 additive manufacturing
source: src/vibey_tools/skills/plugins/manufacturing-mechanical-engineering-for-software-devs/skills/mfg-process-families-machining-additive-and-moulding/SKILL.md
requires: ["skill-12-joining-f46c479225"]
links: ["skill-14-injection-moulding-f1de7646f9"]
---

## §13. Additive Manufacturing

```
⚠️ FDM/FFF  extruded thermoplastic. ⚠️ ANISOTROPIC — much weaker
   between layers, so print orientation is a structural decision
SLA / DLP / vat photopolymerization  ⚠️ excellent resolution; resins
   are often brittle and UV-sensitive
SLS  powder bed polymer, ⚠️ no support structures needed
⚠️ LPBF / SLM  metal laser powder bed — ⚠️ the dominant industrial
   metal process. Requires supports, stress relief, and usually
   post-machining of critical surfaces
BINDER JETTING (MBJ) · DED (⚠️ good for repair and large parts) ·
E-BEAM
```
**⚠️ Where AM genuinely wins**: ⚠️ **geometry impossible by other means (internal channels,
lattices), PART CONSOLIDATION (an assembly of 20 parts becoming one — eliminating
fasteners, welds, assembly labour and failure points), one-offs and spares, and cases
where LEAD TIME matters more than unit cost.**
**⚠️ Where it loses**: ⚠️ **anything simple in volume.** **⚠️ Injection moulding, stamping,
casting and machining all beat it at scale** (§9, §25.1 → `mfg-reference`).
**⚠️ The realities that catch people**: ⚠️ **surface finish usually needs post-processing;
support removal is labour; metal parts need stress relief and often HIP; and
QUALIFICATION for critical parts is the real bottleneck, not printing.**

---
