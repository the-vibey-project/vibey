---
id: skill-3-usb-c-and-power-delivery-5719929265
purpose: 3 usb c and power delivery
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-stack-usb-thunderbolt-and-wireless/SKILL.md
requires: ["skill-2-usb-architecture-2e23bf19bb"]
links: ["skill-4-thunderbolt-and-alternate-modes-cd7a050602"]
---

## §3. ⚠️ USB-C and Power Delivery

> **⚠️ The connector that solved the plug-orientation problem and created a capability-
> discovery problem.**
```
⚠️ THE CONNECTOR  24 pins, reversible, ⚠️ with the CC (Configuration
   Channel) pins doing orientation detection, role detection and
   PD communication
⚠️ ⚠️ USB-C IS A CONNECTOR, NOT A CAPABILITY. ⚠️ A USB-C port may
   carry USB 2.0 only. This is legal and common on cheap devices
⚠️ POWER DELIVERY  ⚠️ negotiated over CC using BMC-encoded
   messaging. ⚠️ Source advertises PDOs (power data objects),
   sink requests one
   ⚠️ FIXED PDOs at 5/9/15/20 V · ⚠️ PPS (programmable power
   supply) for fine-grained voltage — ⚠️ which is what enables
   efficient direct battery charging
   ⚠️ PD 3.1 EPR extends to 28/36/48 V for up to 240 W
⚠️ ⚠️ E-MARKER CHIPS  ⚠️ cables above 3 A contain a chip declaring
   their rating. ⚠️ A cable without one is limited to 3 A
   regardless of construction — the cable is an ACTIVE
   PARTICIPANT in the negotiation
⚠️ ⚠️ Vbus is 5 V UNTIL NEGOTIATED. ⚠️ This is the safety property
   that makes 48 V over a consumer connector acceptable
⚠️ DATA ROLE vs POWER ROLE are INDEPENDENT and swappable (DRP,
   DRD) — a laptop can charge from a monitor while sending video
⚠️ ⚠️ THE COUNTERFEIT PROBLEM  ⚠️ non-compliant cables and chargers
   have destroyed hardware. ⚠️ Certification and the USB-IF
   product database are the only real defence (§25.1)
```

---
