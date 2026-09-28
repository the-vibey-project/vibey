---
id: skill-15-controllers-and-haptics-e7d35579b6
purpose: 15 controllers and haptics
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-audio-printers-storage-controllers-and-haptics/SKILL.md
requires: ["skill-14-storage-capture-and-everything-else-4fb324bfba"]
links: []
---

## §15. Controllers and Haptics

**⚠️ Gamepads**: ⚠️ **analog sticks (potentiometers, and now Hall-effect to eliminate
DRIFT — which is caused by potentiometer wear and contamination), triggers, rumble.**
**⚠️ Standards fragmentation is the practical problem**: ⚠️ **XInput versus DirectInput
versus HID gamepad, with Steam Input and SDL acting as translation layers because no
single standard won.**
**⚠️ Haptics**: ⚠️ **ERM (eccentric rotating mass — cheap, slow to spin up) versus LRA
(linear resonant actuator — fast, precise, narrow frequency) versus piezo; ⚠️ and the
quality difference is mostly in the DRIVE WAVEFORM, not the motor.**
**⚠️ Force feedback** in wheels and flight controls, ⚠️ **and accessibility controllers**
(§23 → `periph-compliance-accessibility-and-security`).

---

# PART III — BUILDING ONE
