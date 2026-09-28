---
id: skill-23-failure-at-scale-9aa5db441a
purpose: 23 failure at scale
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-datacentre-network-storage-failure-and-operations/SKILL.md
requires: ["skill-22-storage-at-scale-bb237dc58a"]
links: ["skill-24-operations-f04e2206d7"]
---

## §23. ⚠️ Failure at Scale

> **⚠️ At scale, rare events are constant. A failure rate that is negligible for one machine
> is a daily occurrence across a hundred thousand.**
```
⚠️ WHAT ACTUALLY FAILS  ⚠️ drives (predictably, at known rates) ·
   ⚠️ DRAM (⚠️ correctable and uncorrectable errors are far more
   common than most people assume — which is why ECC is not
   optional at scale, and soft errors are physics, not defects) ·
   PSUs · fans · optics and cables (⚠️ a large share of "network"
   problems) · ⚠️ and SOFTWARE and HUMAN ERROR, which dominate
   real outage causes
⚠️ CORRELATED FAILURE IS THE KILLER  ⚠️ same batch, same firmware
   bug, same rack, same power feed, same cooling loop.
   ⚠️ Independence is an ASSUMPTION and it is often false
⚠️ DESIGN RESPONSES  ⚠️ design for failure rather than against it ·
   fault domains and availability zones · ⚠️ blast radius
   limitation · graceful degradation · ⚠️ CHAOS ENGINEERING
⚠️ THE HONEST OBSERVATION  ⚠️ most large outages are triggered by
   a CHANGE — a deployment, a config push, a maintenance action —
   not by spontaneous hardware failure. ⚠️ Which means change
   management is reliability engineering
```

---
