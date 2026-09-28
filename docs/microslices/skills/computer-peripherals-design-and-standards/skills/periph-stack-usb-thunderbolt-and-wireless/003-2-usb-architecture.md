---
id: skill-2-usb-architecture-2e23bf19bb
purpose: 2 usb architecture
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-stack-usb-thunderbolt-and-wireless/SKILL.md
requires: ["skill-1-the-peripheral-stack-cc98cad3df"]
links: ["skill-3-usb-c-and-power-delivery-5719929265"]
---

## §2. ⚠️ USB Architecture

```
⚠️ THE TOPOLOGY  a tiered star; ⚠️ one host controller, hubs,
   devices. ⚠️ Max 127 devices, 7 tiers
⚠️ ⚠️ THE HOST POLLS. Devices cannot speak unbidden — which is why
   an interrupt endpoint's POLLING INTERVAL sets input latency
⚠️ ENDPOINTS AND TRANSFER TYPES — ⚠️ the distinction that matters
   ⚠️ CONTROL  enumeration and configuration; guaranteed
   ⚠️ INTERRUPT  ⚠️ small, periodic, BOUNDED LATENCY, guaranteed
      bandwidth. ⚠️ Keyboards and mice (§8)
   ⚠️ BULK  ⚠️ large, reliable, NO timing guarantee — uses whatever
      bandwidth is left. Storage and printers
   ⚠️ ISOCHRONOUS  ⚠️ guaranteed BANDWIDTH and timing, NO error
      correction. ⚠️ Audio and video, where a late packet is
      worse than a lost one
⚠️ SPEEDS  Low 1.5 Mbps · Full 12 · High 480 · SuperSpeed 5 ·
   10 · 20 · ⚠️ USB4 40 and 80 (§25.1)
⚠️ ⚠️ THE NAMING DISASTER  ⚠️ USB 3.0 → 3.1 Gen 1 → 3.2 Gen 1x1
   all describe THE SAME 5 Gbps. ⚠️ The USB-IF renamed the same
   thing twice, and the current fix is to abandon version
   numbers for SPEED LABELS (§25.1)
⚠️ POWER  ⚠️ default 500 mA (USB 2) / 900 mA (USB 3) until
   negotiated. ⚠️ Everything above that requires PD (§3)
```

---
