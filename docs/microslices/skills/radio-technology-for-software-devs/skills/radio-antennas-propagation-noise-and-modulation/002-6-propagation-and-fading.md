---
id: skill-6-propagation-and-fading-5018edd42f
purpose: 6 propagation and fading
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-antennas-propagation-noise-and-modulation/SKILL.md
requires: ["skill-5-antennas-0773353362"]
links: ["skill-7-noise-and-interference-fde3733375"]
---

## §6. Propagation and Fading

```
FREE SPACE      the §3 baseline. ⚠️ You will not get it
REFLECTION      off ground, walls, metal
⚠️ MULTIPATH    copies arrive at different times and phases and INTERFERE.
                Can add or CANCEL
DIFFRACTION     ⚠️ bending around edges — why you get signal around corners.
                Better at low frequencies
SCATTERING      off rough surfaces, rain, foliage
⚠️ FRESNEL ZONE the ellipsoid around the line of sight that must be ~60%
                clear. ⚠️ Visual line of sight is NOT enough for a long link
ABSORPTION      ⚠️ water absorbs strongly. Foliage, rain and people are
                lossy — and 2.4 GHz is near a water absorption feature
```
**⚠️ Fading is the thing that makes RF bugs irreproducible:**
- **⚠️ FAST fading (Rayleigh/Rician)** — **multipath nulls occur on the scale of HALF A
  WAVELENGTH.** ⚠️ **At 2.4 GHz that's about 6 cm.** **Move the device a few centimetres
  and the link can go from fine to dead. This is not a defect.**
- **SLOW fading (shadowing)** — **obstacles, log-normal distributed.**
- **⚠️ Doppler** — **movement shifts frequency and changes the channel over time.**

**⚠️ The mitigations, and all of them are just diversity in some dimension:**
**spatial (multiple antennas — MIMO), frequency (hop or spread — §10 → `radio-spread-spectrum-ofdm-access-and-sdr`, §11 → `radio-spread-spectrum-ofdm-access-and-sdr`), time
(interleave and retransmit — §12 → `radio-spread-spectrum-ofdm-access-and-sdr`), and polarization.** ⚠️ **Antenna diversity — two
antennas a few centimetres apart — is often the single highest-value fix for an
intermittent indoor link, precisely because the nulls are that small.**

---
