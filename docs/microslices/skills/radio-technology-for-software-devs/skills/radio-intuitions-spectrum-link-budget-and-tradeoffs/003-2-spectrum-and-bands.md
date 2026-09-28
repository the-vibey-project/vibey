---
id: skill-2-spectrum-and-bands-9563eb026a
purpose: 2 spectrum and bands
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-intuitions-spectrum-link-budget-and-tradeoffs/SKILL.md
requires: ["skill-1-why-wireless-breaks-software-intuitions-7dda61c5b5"]
links: ["skill-3-the-link-budget-0834845d0c"]
---

## §2. Spectrum and Bands

```
λ = c / f      ⚠️ c ≈ 3×10⁸ m/s.  At 2.4 GHz, λ ≈ 12.5 cm
```
⚠️ **Wavelength determines antenna size** — **an efficient antenna is a meaningful fraction
of a wavelength (¼λ is the classic), which is why low-frequency radios need big antennas
and why your 2.4 GHz chip antenna can be a few centimetres of PCB trace.**

```
BAND        TYPICAL USE                      ⚠️ CHARACTER
LF/MF/HF    AM radio, maritime, amateur      ⚠️ Long range, ground wave and
  <30 MHz                                    ionospheric skip, tiny bandwidth
VHF 30–300M FM, aviation, marine, ham        Good building penetration
UHF 300M–3G ⚠️ 433/868/915 ISM, LoRa, cell,  ⚠️ THE workhorse. Reasonable
            Wi-Fi 2.4, BLE, Zigbee           penetration and antenna size
SHF 3–30G   Wi-Fi 5/6E/7, radar, satellite,  ⚠️ Wide bandwidth, poor
            5G mmWave lower                  penetration, more directional
EHF >30G    ⚠️ mmWave 5G, automotive radar   Enormous bandwidth, blocked by
                                             a hand, absorbed by rain
```
**⚠️ The universal tradeoff, and it's physics, not engineering:**
⚠️ **Lower frequency → better penetration and diffraction, longer range for the same
power, less available bandwidth, bigger antennas.**
⚠️ **Higher frequency → more bandwidth, higher data rates, shorter range, blocked by
walls and bodies, smaller antennas.**
**⚠️ There is no band that is good at everything, and every protocol in §18–§22 → `radio-protocol-stacks-wifi-ble-lpwan-and-gnss` is a
different point on this curve.**

---
