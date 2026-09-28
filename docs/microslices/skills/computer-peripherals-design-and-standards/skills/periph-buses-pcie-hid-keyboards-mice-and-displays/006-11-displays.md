---
id: skill-11-displays-ace928c986
purpose: 11 displays
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-buses-pcie-hid-keyboards-mice-and-displays/SKILL.md
requires: ["skill-10-mice-and-pointing-devices-7cb9241541"]
links: []
---

## §11. Displays

```
⚠️ PANEL TECHNOLOGIES  ⚠️ TN (fast, poor angles) · IPS (colour,
   angles) · VA (contrast, slower transitions) · ⚠️ OLED /
   QD-OLED (per-pixel emission, true blacks, ⚠️ burn-in risk) ·
   miniLED backlights with local dimming
⚠️ THE SPECS THAT ARE ROUTINELY MISREPRESENTED
   ⚠️ RESPONSE TIME  ⚠️ quoted as best-case GtG with overdrive
      that causes INVERSE GHOSTING. Independent measurement is
      the only reliable source
   ⚠️ CONTRAST  ⚠️ "dynamic" figures are meaningless; native
      contrast is the real number
   ⚠️ HDR  ⚠️ the lower certification tiers are near-meaningless
      on a display without local dimming
   ⚠️ REFRESH RATE  ⚠️ a panel's rate and the INTERFACE bandwidth
      needed to feed it are different problems (§25.2)
⚠️ VARIABLE REFRESH  ⚠️ adaptive sync — the display refreshes when
   the frame is ready rather than on a fixed clock. ⚠️ The
   REFRESH RANGE and whether LFC (low framerate compensation)
   exists matter more than the badge
⚠️ ⚠️ DSC (Display Stream Compression)  ⚠️ visually lossless,
   hardware, ~3:1, microsecond latency — ⚠️ NOT streaming-style
   compression. ⚠️ It is how high modes fit in limited pipes,
   and it is genuinely fine, with the caveats in §25.2
⚠️ COLOUR  gamut (sRGB/DCI-P3/Rec.2020) · bit depth and ⚠️ FRC
   dithering ("10-bit" often means 8-bit+FRC) · calibration
   and ICC profiles · EDID/DisplayID as the display's descriptor
```
