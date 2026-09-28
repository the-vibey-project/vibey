---
id: skill-2-propagation-and-the-link-budget-7a4c4eab1c
purpose: 2 propagation and the link budget
source: src/vibey_tools/skills/plugins/wireless-technologies-and-rf-engineering/skills/wireless-propagation-link-budget-modulation-antennas-and-spectrum/SKILL.md
requires: ["skill-1-why-wireless-is-hard-62eb1e0716"]
links: ["skill-3-modulation-and-multiple-access-0fc55eaf3d"]
---

## §2. ⚠️ Propagation and the Link Budget

> **⚠️ If you learn one thing here, learn this. It predicts more than any amount of
> protocol knowledge.**
```
⚠️ THE BUDGET  ⚠️ Received power (dBm) = TX power + TX antenna gain
   − path loss − losses + RX antenna gain
   ⚠️ LINK MARGIN = received power − receiver sensitivity.
   ⚠️ You want meaningful margin, not a bare pass
⚠️ ⚠️ dB THINKING  ⚠️ +3 dB doubles power · +10 dB is 10× ·
   ⚠️ −3 dB halves it. ⚠️ dBm is absolute (0 dBm = 1 mW), dB and
   dBi are ratios. ⚠️ Confusing them is the classic beginner error
⚠️ FREE SPACE PATH LOSS  ⚠️ rises with the SQUARE of distance AND
   the SQUARE of frequency. ⚠️ Doubling distance costs 6 dB
   ⚠️ THIS IS WHY 2.4 GHz REACHES FURTHER THAN 5 GHz, which
   reaches further than 6 GHz — ⚠️ pure physics, not
   implementation quality
⚠️ REAL ENVIRONMENTS ARE WORSE  ⚠️ path loss exponent in buildings
   is well above the free-space value
   ⚠️ ABSORPTION  ⚠️ WATER absorbs 2.4 GHz strongly — which is why
      human bodies, aquariums and foliage are real obstacles, and
      why body-worn devices behave differently on-body
   ⚠️ REFLECTION and MULTIPATH  ⚠️ copies arriving at different
      times cause FADING — and multipath can be destructive
      enough that moving 20 cm fixes a "broken" link
   ⚠️ DIFFRACTION and the Fresnel zone · penetration losses
      (⚠️ concrete, metal, low-E glass and foil insulation are
      severe; ⚠️ modern energy-efficient windows can be near
      RF-opaque, which surprises people)
⚠️ FADING  ⚠️ slow (shadowing) vs FAST (multipath) · Rayleigh vs
   Rician. ⚠️ Diversity and MIMO exist to exploit this rather
   than fight it
⚠️ NOISE FLOOR and SNR  ⚠️ sensitivity improves as data rate falls
   — ⚠️ which is why every technology has a rate-versus-range
   curve and drops rate automatically at the edge
```

---
