---
id: skill-4-antennas-e643a11461
purpose: 4 antennas
source: src/vibey_tools/skills/plugins/wireless-technologies-and-rf-engineering/skills/wireless-propagation-link-budget-modulation-antennas-and-spectrum/SKILL.md
requires: ["skill-3-modulation-and-multiple-access-0fc55eaf3d"]
links: ["skill-5-spectrum-and-regulation-662251d1a0"]
---

## §4. ⚠️ Antennas

**⚠️ See an electromagnetism reference for the field theory. Here, what matters in
practice.**
```
⚠️ THE KEY PARAMETERS
   ⚠️ GAIN is NOT amplification — ⚠️ it is DIRECTIONALITY. An
      antenna is passive; gain in one direction is loss in
      another. ⚠️ dBi vs dBd (2.15 dB apart)
   ⚠️ RADIATION PATTERN  ⚠️ and a high-gain omni antenna gets its
      gain by SQUASHING the pattern vertically — which is why it
      can perform WORSE for a device above or below it
   ⚠️ POLARIZATION  ⚠️ cross-polarization loss is severe. ⚠️ A
      vertical and a horizontal antenna couple poorly, which is
      part of why phone orientation changes signal
   ⚠️ IMPEDANCE MATCH, VSWR, RETURN LOSS  ⚠️ a mismatched antenna
      reflects power back rather than radiating it
   ⚠️ BANDWIDTH and EFFICIENCY
⚠️ TYPES  ⚠️ monopole/whip · dipole · ⚠️ PCB TRACE (cheap, and
   utterly dependent on ground plane and clearance, §17) ·
   ⚠️ CHIP antennas (small, low efficiency, need a matching
   network) · patch · Yagi · parabolic · slot
⚠️ ⚠️ THE GROUND PLANE IS PART OF THE ANTENNA. ⚠️ A quarter-wave
   monopole needs a ground plane to work at all — and on a small
   product, the PCB ground plane IS the other half of the
   antenna. ⚠️ Shrinking the board changes the antenna
⚠️ THE FUNDAMENTAL LIMIT  ⚠️ small antennas are inherently
   narrowband and inefficient (Chu-Harrington). ⚠️ You cannot
   design your way out of this — physics caps it
```

---
