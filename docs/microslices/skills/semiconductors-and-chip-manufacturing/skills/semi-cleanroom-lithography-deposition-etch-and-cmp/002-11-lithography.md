---
id: skill-11-lithography-c07bf1feed
purpose: 11 lithography
source: src/vibey_tools/skills/plugins/semiconductors-and-chip-manufacturing/skills/semi-cleanroom-lithography-deposition-etch-and-cmp/SKILL.md
requires: ["skill-10-the-cleanroom-3fd0cb40a2"]
links: ["skill-12-deposition-5e196b5f9c"]
---

## §11. ⚠️ Lithography

> **⚠️ The crown jewel and the industry's tightest chokepoint. Everything else in the fab
> exists to support what lithography defines.**
```
⚠️ THE BASIC CYCLE  coat photoresist → EXPOSE through a mask →
   develop → etch or implant → strip. ⚠️ Repeated dozens of times,
   with each layer aligned to the last within nanometres (OVERLAY)
⚠️ RESOLUTION  ⚠️ Rayleigh: CD = k₁ · λ/NA. ⚠️ You improve
   resolution by shortening WAVELENGTH, raising NUMERICAL APERTURE,
   or reducing k₁ through process tricks
⚠️ THE WAVELENGTH LADDER  436nm → 365nm → 248nm (KrF) →
   ⚠️ 193nm (ArF) → 193nm IMMERSION (water raises effective NA)
   → ⚠️ 13.5nm EUV
⚠️ ⚠️ 193nm IMMERSION PRINTED FEATURES FAR BELOW 193nm for years
   via MULTIPLE PATTERNING — ⚠️ splitting one layer across two,
   three or four masks and exposures. ⚠️ Each additional pattern
   adds masks, alignment error budget, etch steps and cost
⚠️ EUV  ⚠️ 13.5nm, and it required inventing an entire ecosystem:
   ⚠️ tin droplets vaporized by a high-power laser to make plasma ·
   ⚠️ ALL-REFLECTIVE optics (everything absorbs EUV, including air —
   so the whole beam path is in VACUUM) · ⚠️ multilayer Bragg
   mirrors, each losing energy · ⚠️ reflective masks with pellicle
   difficulties
⚠️ RESOLUTION ENHANCEMENT  ⚠️ OPC (deliberately distorting the mask
   so the printed result is correct), phase-shift masks, source-mask
   optimization, inverse lithography
⚠️ STOCHASTICS  ⚠️ at EUV doses, PHOTON SHOT NOISE becomes a real
   defect mechanism — you are counting individual photons and
   random variation causes random failures
```
**⚠️ ASML is the sole supplier of EUV**, ⚠️ **with Zeiss the sole supplier of the optics —
which is the single most concentrated dependency in the modern economy** (§26 → `semi-pcb-assembly-reliability-design-flow-and-economics`, §27.1 → `semi-reference`).

---
