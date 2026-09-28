---
id: skill-14-troubleshooting-ad1ed73cf4
purpose: 14 troubleshooting
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-specifying-assembly-firmware-tuning-and-benchmarking/SKILL.md
requires: ["skill-13-tuning-and-overclocking-honestly-24770cb634"]
links: ["skill-15-benchmarking-89834430a7"]
---

## §14. ⚠️ Troubleshooting

```
⚠️ THE METHOD  ⚠️ change ONE thing at a time · bisect · reduce to
   minimum configuration · swap known-good parts · ⚠️ and READ
   THE ACTUAL ERROR before theorizing
⚠️ NO POST  ⚠️ power connectors (especially the CPU 8-pin, the
   most commonly forgotten) · RAM reseat and try ONE stick ·
   standoff short · ⚠️ CMOS clear · debug LEDs or POST codes
   (⚠️ these tell you the stage — use them)
⚠️ RANDOM CRASHES  ⚠️ this is the hardest class. ⚠️ Suspect, in
   rough order: PSU transients (§7) · RAM (⚠️ run MemTest86
   OVERNIGHT — a short pass proves little) · thermals · unstable
   XMP · drivers · storage errors
⚠️ THERMAL THROTTLING  monitor under sustained load, not at idle
⚠️ POOR PERFORMANCE  ⚠️ check XMP enabled · dual channel populated ·
   GPU in the CPU-attached x16 slot · power plan · background load ·
   ⚠️ and confirm which resource is actually saturated (§15)
⚠️ INTERMITTENT  ⚠️ the worst. Log everything; check event logs;
   suspect connections, thermal cycling and marginal power
⚠️ ⚠️ THE PRINCIPLE: SUSPECT WHAT YOU CHANGED, and prefer
   measurement over replacement
```

---
