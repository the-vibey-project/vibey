---
id: skill-9-keyboards-16c2ba5598
purpose: 9 keyboards
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-buses-pcie-hid-keyboards-mice-and-displays/SKILL.md
requires: ["skill-8-hid-fa00d40792"]
links: ["skill-10-mice-and-pointing-devices-7cb9241541"]
---

## §9. ⚠️ Keyboards

```
⚠️ SWITCH TYPES  ⚠️ mechanical (linear / tactile / clicky) ·
   membrane / rubber dome · scissor · ⚠️ optical and Hall-effect
   (⚠️ contactless, enabling ADJUSTABLE ACTUATION POINT and
   rapid trigger)
⚠️ THE MATRIX  ⚠️ rows and columns scanned to reduce pin count
⚠️ ⚠️ GHOSTING AND BLOCKING  ⚠️ without isolation diodes, three
   keys in a rectangle make a phantom fourth appear.
   ⚠️ A DIODE PER SWITCH gives full NKRO. ⚠️ "Anti-ghosting" in
   marketing usually means BLOCKING (refusing the ambiguous
   input) rather than true NKRO
⚠️ ⚠️ 6KRO vs NKRO  ⚠️ 6KRO is not a hardware limit — it's the HID
   BOOT PROTOCOL report format (§8). ⚠️ NKRO requires a custom
   descriptor, which is why some NKRO keyboards fail in BIOS
   and offer a toggle
⚠️ DEBOUNCE  ⚠️ mechanical contacts bounce for milliseconds.
   ⚠️ Debounce algorithm and window are a REAL latency
   contributor and a real design trade — too short gives double
   presses, too long adds delay
⚠️ SCAN RATE and USB POLLING are separate: ⚠️ a fast matrix scan
   gains nothing if the endpoint is polled at 125 Hz (§21)
⚠️ LAYOUT and PROFILE  ⚠️ ANSI/ISO/JIS · Cherry, OEM, SA, DSA
   keycap profiles · ⚠️ MX vs Topre vs low-profile stems
⚠️ PCB, PLATE, MOUNTING  ⚠️ gasket, top, tray, integrated —
   these determine acoustics and flex, which is most of what
   enthusiasts actually care about
```

---
