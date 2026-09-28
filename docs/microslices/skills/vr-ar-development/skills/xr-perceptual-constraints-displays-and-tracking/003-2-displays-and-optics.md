---
id: skill-2-displays-and-optics-f374770dd2
purpose: 2 displays and optics
source: src/vibey_tools/skills/plugins/vr-ar-development/skills/xr-perceptual-constraints-displays-and-tracking/SKILL.md
requires: ["skill-1-the-perceptual-constraints-c277bfa210"]
links: ["skill-3-tracking-f3ef506358"]
---

## §2. Displays and Optics

**The metrics that matter**, and ⚠️ **note that FOV and PPD trade against each other for a
fixed panel:**
```
FOV                horizontal/vertical, per-eye and combined
⚠️ PPD (pixels per degree)   THE resolution metric — human acuity is ~60 PPD
Refresh rate       72 / 90 / 120 Hz
Persistence        ⚠️ low-persistence illumination (~2 ms) prevents smearing during
                   head motion — a critical and under-appreciated property
IPD                interpupillary distance ⚠️ — wrong IPD causes eye strain and
                   distorts perceived scale
```
**Panel technologies**: LCD, OLED, **micro-OLED / OLED-on-silicon** (⚠️ **the current
high-end standard**), and **MicroLED** in development for brightness and efficiency.

**Optics**: Fresnel (⚠️ **god rays and glare**), **pancake lenses** (⚠️ **thinner and
sharper, at a significant light-efficiency cost — which is why pancake headsets need
brighter panels**), and for AR: **waveguides** (diffractive/reflective — ⚠️ **the only
practical path to glasses form factor, and they cost you FOV, brightness and colour
uniformity**) vs **birdbath** (better image, bulkier).

**⚠️ Optical distortion correction is mandatory and it is not free**: lenses distort, so
you render and then apply an inverse barrel distortion, **with per-channel correction for
chromatic aberration.** ⚠️ **This is why you never render at exactly display resolution —
distortion resampling means the source must be supersampled to avoid losing detail in the
centre.**

**AR display modes**: **optical see-through** (⚠️ **you cannot render black — additive
only, so occlusion of real objects is physically impossible**) vs **video passthrough**
(⚠️ **full control and true occlusion, but the passthrough camera's own latency now sits
in the user's view of the real world**).

---
