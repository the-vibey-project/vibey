---
id: skill-5-wireless-peripherals-fe83353333
purpose: 5 wireless peripherals
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-stack-usb-thunderbolt-and-wireless/SKILL.md
requires: ["skill-4-thunderbolt-and-alternate-modes-cd7a050602"]
links: []
---

## §5. Wireless Peripherals

**⚠️ Bluetooth**: ⚠️ **Classic versus LE; ⚠️ HID over GATT for LE devices; ⚠️ and the
CONNECTION INTERVAL is the latency parameter that matters, negotiated between devices and
often conservative by default.**
**⚠️ Proprietary 2.4 GHz dongles** exist because ⚠️ **they can use shorter intervals,
frequency hopping tuned for latency rather than coexistence, and skip Bluetooth's
pairing and stack overhead — which is why competitive gaming peripherals ship dongles
rather than relying on Bluetooth.**
**⚠️ The real-world problems**: ⚠️ **2.4 GHz congestion (Wi-Fi, microwaves), USB 3 port
RADIATED NOISE desensitizing 2.4 GHz receivers (⚠️ a genuine and well-documented effect —
move the dongle away from USB 3 ports), latency variance rather than mean, and battery
management.**
**⚠️ Wireless is now competitive with wired for latency in good implementations** —
⚠️ **the remaining honest arguments for wired are power, reliability under congestion, and
not having a battery.**
