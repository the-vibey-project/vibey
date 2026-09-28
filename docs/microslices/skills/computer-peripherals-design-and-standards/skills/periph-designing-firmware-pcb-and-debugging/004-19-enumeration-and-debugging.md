---
id: skill-19-enumeration-and-debugging-5b93883665
purpose: 19 enumeration and debugging
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-designing-firmware-pcb-and-debugging/SKILL.md
requires: ["skill-18-pcb-and-mechanical-design-60162855c8"]
links: ["skill-20-drivers-and-os-integration-e4838fa83e"]
---

## §19. ⚠️ Enumeration and Debugging

> **⚠️ Where most peripheral development time actually goes.**
```
⚠️ THE ENUMERATION SEQUENCE  ⚠️ attach and speed detection via
   pull-ups → reset → address assignment → ⚠️ DEVICE DESCRIPTOR
   read → configuration, interface, endpoint descriptors →
   ⚠️ HID REPORT DESCRIPTOR → configuration selected → operational
⚠️ ⚠️ ALMOST EVERY "DEVICE NOT RECOGNIZED" IS A DESCRIPTOR OR
   POWER PROBLEM. ⚠️ A malformed report descriptor typically
   fails SILENTLY — the device enumerates and then does nothing,
   or does something bizarre
⚠️ THE TOOLS, in order of usefulness
   ⚠️ lsusb -v / USBView / USB Prober — ⚠️ read the actual
      descriptors first, always
   ⚠️ HID descriptor validators and parsers
   ⚠️ Wireshark with usbmon (Linux) — ⚠️ free protocol capture
   ⚠️ Hardware protocol analysers — expensive and decisive
   ⚠️ OSCILLOSCOPE for physical-layer problems, ⚠️ and eye
      diagrams for signal integrity
⚠️ THE COMMON FAULTS  ⚠️ descriptor length mismatches · wrong
   usage page · endpoint size vs report size disagreement ·
   ⚠️ requesting more current than declared · missing or wrong
   pull-ups · ⚠️ bus-powered device browning out on inrush ·
   host controller quirks that differ across OSes
⚠️ ⚠️ TEST ON ALL TARGET PLATFORMS. ⚠️ Windows, macOS, Linux, BIOS
   and phones parse descriptors differently and tolerate
   different sloppiness
```

---
