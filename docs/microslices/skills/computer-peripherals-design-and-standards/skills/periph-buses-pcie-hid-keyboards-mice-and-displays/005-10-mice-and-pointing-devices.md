---
id: skill-10-mice-and-pointing-devices-7cb9241541
purpose: 10 mice and pointing devices
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-buses-pcie-hid-keyboards-mice-and-displays/SKILL.md
requires: ["skill-9-keyboards-16c2ba5598"]
links: ["skill-11-displays-ace928c986"]
---

## §10. Mice and Pointing Devices

**⚠️ Sensors**: ⚠️ **optical (LED or laser) taking thousands of surface images per second
and correlating them; ⚠️ the specs that matter are max tracking speed, max acceleration,
and lift-off distance.**
> **⚠️ GOTCHA — DPI IS A MARKETING NUMBER PAST A POINT.** ⚠️ **Very high DPI settings are
> frequently interpolated rather than native, and no one uses 30,000 DPI.** **⚠️ What
> matters is sensor accuracy — absence of smoothing, acceleration and angle snapping —
> which cheap sensors add to hide their deficiencies.**

**⚠️ Polling rate**: ⚠️ **125/500/1000 Hz and now 4/8 kHz; ⚠️ the returns diminish sharply
and high rates cost CPU and battery** (§21 → `periph-designing-firmware-pcb-and-debugging`).
**⚠️ Switches** are the wear item — ⚠️ **DOUBLE-CLICKING from switch degradation is the
characteristic failure mode of otherwise-good mice, and is repairable.**
**⚠️ Other pointing devices**: ⚠️ **trackballs, trackpads (⚠️ capacitive multitouch with
substantial gesture processing in firmware or driver), graphics tablets (⚠️ EMR — the
pen is passive and powered by the tablet's field), and touchscreens.**

---
