---
id: skill-21-rf-debugging-9b346ccab2
purpose: 21 rf debugging
source: src/vibey_tools/skills/plugins/wireless-technologies-and-rf-engineering/skills/wireless-antenna-integration-certification-low-power-and-debugging/SKILL.md
requires: ["skill-20-provisioning-and-onboarding-989600fcb7"]
links: []
---

## §21. ⚠️ RF Debugging

```
⚠️ THE TOOLS, in rough order of value per pound
   ⚠️ SPECTRUM ANALYSER  ⚠️ see what is actually in the band —
      including the interferer you didn't know about (§23)
   ⚠️ PROTOCOL SNIFFER  ⚠️ nRF Sniffer for BLE · Wireshark with
      a monitor-mode Wi-Fi adapter · Ubertooth
   ⚠️ VNA  antenna matching and return loss (§17)
   ⚠️ SDR  ⚠️ an RTL-SDR is remarkably capable for the price and
      is the best entry point into seeing RF at all
   ⚠️ Current profiler (§19) · logic analyser for the digital side
⚠️ THE METHOD  ⚠️ ISOLATE THE LAYER FIRST. ⚠️ Is it RF (link
   quality), protocol (connection/negotiation), or application?
   ⚠️ RSSI and packet error rate together distinguish them
⚠️ ⚠️ TEST AT RANGE AND IN THE REAL ENVIRONMENT. ⚠️ Everything
   works on a bench 30 cm apart, and that proves nothing
⚠️ THE CLASSIC CULPRITS  ⚠️ antenna detuned by the enclosure (§17)
   · ⚠️ ground plane too small · missing keepout · ⚠️ power supply
   noise and inadequate decoupling · ⚠️ SWITCHING REGULATOR
   harmonics landing in band · unshielded high-speed digital
   lines · ⚠️ USB 3 noise desensitizing 2.4 GHz (§23)
⚠️ ⚠️ GOLDEN UNITS  keep known-good reference hardware, because
   "it got worse" is unanswerable without a baseline
```

---

# PART IV — CROSS-CUTTING
