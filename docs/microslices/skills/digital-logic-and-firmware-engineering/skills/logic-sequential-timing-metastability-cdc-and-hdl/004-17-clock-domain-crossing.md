---
id: skill-17-clock-domain-crossing-70ed7c2afb
purpose: 17 clock domain crossing
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-sequential-timing-metastability-cdc-and-hdl/SKILL.md
requires: ["skill-16-state-machines-0d3b707caf"]
links: ["skill-18-hdl-and-synthesis-14bb09b7b7"]
---

## §17. ⚠️ Clock Domain Crossing

> **⚠️ Where §15's metastability becomes a design discipline rather than an analysis.**
```
⚠️ THE PROBLEM  ⚠️ a signal generated in one clock domain and
   sampled in another has NO timing relationship. ⚠️ Setup and
   hold WILL be violated eventually — it is a matter of
   probability, not possibility
⚠️ ⚠️ THIS IS THE CLASSIC SOURCE OF "WORKS ON THE BENCH, FAILS
   IN THE FIELD" BUGS. ⚠️ An unsynchronized crossing can run
   correctly for days and then fail
⚠️ THE TECHNIQUES
   ⚠️ TWO-FLOP SYNCHRONIZER  ⚠️ for SINGLE-BIT LEVEL signals only
   ⚠️ PULSE SYNCHRONIZER / toggle synchronizer  for events
   ⚠️ ⚠️ MULTI-BIT DATA CANNOT USE A SIMPLE SYNCHRONIZER —
      ⚠️ each bit resolves independently, so you can capture a
      value that never existed. ⚠️ THIS IS THE MOST DANGEROUS
      CDC MISTAKE
      ⚠️ Use: ⚠️ GRAY CODE (only one bit changes, so a bad
      sample is at worst the old or new value) · ⚠️ handshake ·
      ⚠️ ASYNCHRONOUS FIFO — the standard solution for streams
   ⚠️ RESET SYNCHRONIZATION (§14)
⚠️ ⚠️ CDC VERIFICATION TOOLS EXIST AND SHOULD BE RUN. ⚠️ Static
   CDC analysis finds unsynchronized crossings that simulation
   will not, because simulation does not model metastability
```

---
