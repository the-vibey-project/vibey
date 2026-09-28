---
id: skill-19-bluetooth-and-ble-87f7d48fa0
purpose: 19 bluetooth and ble
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-protocol-stacks-wifi-ble-lpwan-and-gnss/SKILL.md
requires: ["skill-18-wi-fi-802-11-7b131e45bf"]
links: ["skill-20-lpwan-and-cellular-iot-4a54bbb8fa"]
---

## §19. Bluetooth and BLE

**⚠️ Classic Bluetooth and BLE are different protocols that share a brand.**
```
BLE       ⚠️ 2.4 GHz, 40 channels × 2 MHz, GFSK, adaptive frequency hopping
   ⚠️ 3 ADVERTISING channels (37/38/39) deliberately placed to dodge the
   most-used Wi-Fi channels
ROLES     Peripheral/Central; Broadcaster/Observer
⚠️ GATT   the data model — Services → Characteristics → Descriptors, each
   with a UUID. ⚠️ This is where most BLE application bugs live
CONNECTION INTERVAL  ⚠️ 7.5 ms–4 s. THE dominant power/latency knob
5.x       ⚠️ 2 Mbps PHY (faster, shorter range) · CODED PHY (LE Long Range,
   ~4× range via FEC) · extended advertising · ⚠️ LE Audio and Auracast ·
   direction finding (AoA/AoD)
```
> **⚠️ GOTCHA — connection interval and slave latency dominate both battery life and
> responsiveness, and they're negotiated, not commanded.** ⚠️ **The central proposes; the
> peripheral requests; and some platforms silently override what you ask for.**
> **iOS in particular enforces its own constraints regardless of your request**, **which
> is why a peripheral behaves differently on Android and iOS with identical firmware.**
> **⚠️ Always read back the ACTUAL negotiated parameters rather than assuming.**

**⚠️ MTU negotiation is the other perennial**: **the default ATT MTU is tiny (23 bytes,
20 usable), and failing to negotiate a larger one silently fragments your data and
destroys throughput.**

---
