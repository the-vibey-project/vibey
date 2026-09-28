---
id: skill-8-fuel-cycle-and-waste-10503d441a
purpose: 8 fuel cycle and waste
source: src/vibey_tools/skills/plugins/nuclear-physics/skills/nuclear-fuel-cycle-waste-and-safety/SKILL.md
requires: []
links: ["skill-9-reactor-safety-cc64e0214d"]
---

## §8. Fuel Cycle and Waste

```
Mining → milling (yellowcake) → conversion (UF₆) → ENRICHMENT → fuel fabrication
  → reactor (⚠️ 3–5 years) → spent fuel pool (⚠️ ~5+ years) → dry cask
    → [reprocessing] or → geological disposal
```
**⚠️ Enrichment** raises `²³⁵U` from natural **0.7%** to **3–5%** for power reactors.
⚠️ **The physics is separation by tiny mass difference, which is why it requires many
stages and is the technically demanding step of the cycle.** **HALEU (5–20%) is required
by many advanced designs, and §16.2 → `nuclear-reference` flags it as the current bottleneck.**

**Waste categories and their real proportions:**
- **⚠️ High-level waste is ~3% of volume and ~95% of radioactivity.** **This is the
  proportion that matters and it is routinely lost in discussion.**
- **Intermediate and low-level** — most of the volume, little of the hazard.
- **⚠️ Radiotoxicity decays sharply**: `⁹⁰Sr` and `¹³⁷Cs` (~30 y) dominate for centuries;
  **the long tail is actinides.** ⚠️ **Partitioning and transmutation could shorten it to
  centuries in principle; it has not been done at scale.**

**⚠️ Reprocessing** (PUREX) recovers uranium and plutonium. ⚠️ **The trade is explicit and
unresolved: it reduces waste volume and extends fuel supply, and it separates plutonium,
which is a proliferation concern. Different countries have made opposite calls on this for
the same reasons.**
**Geological disposal**: ⚠️ **Finland's Onkalo is the first repository to reach operational
readiness; most countries have not solved the siting problem, which is political rather
than technical.**

---
