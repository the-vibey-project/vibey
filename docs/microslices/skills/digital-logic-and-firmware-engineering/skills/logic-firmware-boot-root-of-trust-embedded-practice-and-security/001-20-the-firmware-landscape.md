---
id: skill-20-the-firmware-landscape-f947e2419d
purpose: 20 the firmware landscape
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-firmware-boot-root-of-trust-embedded-practice-and-security/SKILL.md
requires: []
links: ["skill-21-the-boot-sequence-883be5cb1d"]
---

## §20. The Firmware Landscape

```
⚠️ WHAT COUNTS AS FIRMWARE  ⚠️ far more than "the BIOS" —
   ⚠️ platform firmware (UEFI/BIOS) · embedded controller ·
   ⚠️ management engine / PSP (⚠️ a separate processor with
   higher privilege than the CPU, running code you cannot
   inspect) · ⚠️ BMC/service processor · storage controller
   firmware · GPU VBIOS · network card firmware · ⚠️ MICROCODE ·
   peripheral firmware
⚠️ ⚠️ THE UNCOMFORTABLE TRUTH: a modern machine runs a great deal
   of privileged code before and beneath the OS, most of it
   proprietary and unexamined (§25, §26.2)
⚠️ THE SPECTRUM  ⚠️ bare metal → RTOS → embedded Linux
⚠️ WHAT MAKES FIRMWARE DIFFERENT FROM SOFTWARE  ⚠️ it may be the
   only thing running · ⚠️ failure can be unrecoverable (bricking)
   · updates are risky and sometimes one-way · ⚠️ hardware
   constraints are absolute · debugging is hard · ⚠️ lifetimes
   measured in decades
```

---
