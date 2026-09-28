---
id: skill-12-testing-cde13d451c
purpose: 12 testing
source: src/vibey_tools/skills/plugins/automotive-software/skills/auto-process-testing-domains-and-supply-chain/SKILL.md
requires: ["skill-11-process-and-toolchain-01fdb9fa6f"]
links: ["skill-13-the-domains-2952fddafb"]
---

## §12. Testing

```
MIL   Model in the loop        the model against a plant model
SIL   Software in the loop     ⚠️ generated code on a host — catches codegen issues
PIL   Processor in the loop    on the target processor, ⚠️ catches WCET/numeric issues
HIL   Hardware in the loop     ⚠️ real ECU, simulated vehicle in real time
                               THE workhorse of automotive validation
VIL / test bench / proving ground / fleet
```
**⚠️ HIL is where automotive testing actually happens**: the real ECU with real I/O, driven
by a real-time plant model, with **fault injection** — open circuits, shorts to battery and
ground, sensor drift, bus errors. **You can test failure modes that would be dangerous or
destructive on a real vehicle.**

**Other essentials**: **restbus simulation** (⚠️ **simulate every other ECU so you can test
one in isolation — indispensable in a supply chain**), **CAN/Ethernet trace analysis**,
**coverage** (⚠️ **MC/DC required at ASIL D**), **fault injection for safety-mechanism
validation**, **EMC and environmental qualification**, and **durability**.

---
