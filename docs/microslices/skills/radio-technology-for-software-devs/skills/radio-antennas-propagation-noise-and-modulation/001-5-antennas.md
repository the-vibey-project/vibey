---
id: skill-5-antennas-0773353362
purpose: 5 antennas
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-antennas-propagation-noise-and-modulation/SKILL.md
requires: []
links: ["skill-6-propagation-and-fading-5018edd42f"]
---

## §5. Antennas

**⚠️ The most under-appreciated component in the whole system, and usually the cheapest
place to gain 10 dB.**
```
GAIN (dBi)     ⚠️ NOT amplification — it's focusing. A high-gain antenna is
               directional; it robs from one direction to give to another
RADIATION PATTERN  ⚠️ where the energy actually goes. A dipole has a NULL
               along its own axis — point it at the receiver and you get nothing
POLARIZATION   ⚠️ linear (V/H) or circular. CROSS-POLARIZED antennas can cost
               you 20+ dB. This is why an orientation change kills a link
IMPEDANCE / VSWR  ⚠️ mismatch reflects power back. Aim for VSWR < 2:1
GROUND PLANE   ⚠️ many antennas need one and are part of it. Changing the
               PCB changes the antenna
```
> **⚠️ GOTCHA — the enclosure, the PCB, the battery and the human holding it are all part
> of your antenna.** ⚠️ **An antenna tuned on the bench, on a bare board, will detune when
> you put it in a plastic case near a LiPo cell.** **Metal enclosures are close to fatal
> for internal antennas.** **This is why "it worked on the dev board" is such a common and
> expensive surprise** — **and why RF designs get re-tuned after mechanical design
> freezes, not before.**

**Practical rules**: ⚠️ **keep antennas away from ground planes, metal and batteries;
respect the manufacturer's keep-out area exactly; height matters enormously outdoors;
and for a fixed link, aiming a directional antenna is the cheapest dB you will ever buy.**

---
