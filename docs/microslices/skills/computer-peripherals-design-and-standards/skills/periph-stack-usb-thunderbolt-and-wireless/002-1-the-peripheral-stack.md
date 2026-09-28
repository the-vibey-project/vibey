---
id: skill-1-the-peripheral-stack-cc98cad3df
purpose: 1 the peripheral stack
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-stack-usb-thunderbolt-and-wireless/SKILL.md
requires: ["skill-0-routing-f8c28a6986"]
links: ["skill-2-usb-architecture-2e23bf19bb"]
---

## §1. The Peripheral Stack

```
⚠️ THE LAYERS, and problems can live at any of them
   ⚠️ PHYSICAL  connector, cable, differential signalling, power
   ⚠️ LINK  encoding, framing, error handling
   ⚠️ PROTOCOL  transfers, endpoints, enumeration
   ⚠️ DEVICE CLASS  ⚠️ HID, audio, storage, video — the shared
      contract that means you don't need a driver per product
   ⚠️ DRIVER  OS integration
   ⚠️ APPLICATION
⚠️ ⚠️ CLASS DRIVERS ARE WHY PERIPHERALS "JUST WORK". ⚠️ A keyboard
   from any vendor works on any OS because both implement the HID
   class (§8). ⚠️ Vendor-specific drivers exist only where the
   class model is insufficient — or where the vendor wants
   lock-in and telemetry
⚠️ HOST-CENTRIC vs PEER  ⚠️ USB is strictly host-controlled: devices
   NEVER initiate transfers, they are polled. ⚠️ This shapes
   everything about latency (§21) and power
```

---

# PART I — BUSES AND PROTOCOLS
