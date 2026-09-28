---
id: skill-9-ble-programming-c4a14d643e
purpose: 9 ble programming
source: src/vibey_tools/skills/plugins/wireless-technologies-and-rf-engineering/skills/wireless-wifi-bluetooth-ble-nfc-and-rfid/SKILL.md
requires: ["skill-8-bluetooth-6c026af017"]
links: ["skill-10-nfc-and-rfid-15098ee9bb"]
---

## §9. ⚠️ BLE Programming

> **⚠️ The most commonly built wireless application, and the model repays understanding.**
```
⚠️ ⚠️ GATT IS A DATABASE  ⚠️ the peripheral exposes SERVICES,
   each containing CHARACTERISTICS, each with a VALUE and
   DESCRIPTORS. ⚠️ The central reads, writes, or subscribes
⚠️ UUIDs  ⚠️ 16-bit for SIG-adopted services, 128-bit for custom.
   ⚠️ Use adopted services where one exists — heart rate, battery,
   device information — because generic apps will understand them
⚠️ THE OPERATIONS  ⚠️ read · write · WRITE WITHOUT RESPONSE
   (faster, unacknowledged) · ⚠️ NOTIFY (unacknowledged push) ·
   ⚠️ INDICATE (acknowledged push, slower)
   ⚠️ Polling by repeated read is the classic beginner mistake —
   SUBSCRIBE instead
⚠️ ADVERTISING  ⚠️ 31 bytes in a legacy advertising packet, plus
   a scan response. ⚠️ That tight budget shapes beacon design ·
   extended advertising lifts it substantially
⚠️ ⚠️ THROUGHPUT IS GOVERNED BY connection interval, packets per
   interval, MTU and PHY — ⚠️ NOT by the advertised "2 Mbps",
   which is a raw PHY rate. ⚠️ Real application throughput is a
   fraction of it
⚠️ THE STACKS  ⚠️ Zephyr · Nordic nRF Connect SDK · ESP-IDF ·
   Arduino/CircuitPython for prototyping · BlueZ on Linux ·
   ⚠️ Web Bluetooth for browser-based tools
⚠️ DEBUGGING  ⚠️ nRF Connect mobile app for inspecting a GATT
   server · ⚠️ SNIFFERS (nRF Sniffer, Ubertooth) — and a sniffer
   is close to essential for connection-level problems
```

---
