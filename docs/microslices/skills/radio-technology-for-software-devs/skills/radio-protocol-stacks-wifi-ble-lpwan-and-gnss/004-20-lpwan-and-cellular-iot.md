---
id: skill-20-lpwan-and-cellular-iot-4a54bbb8fa
purpose: 20 lpwan and cellular iot
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-protocol-stacks-wifi-ble-lpwan-and-gnss/SKILL.md
requires: ["skill-19-bluetooth-and-ble-87f7d48fa0"]
links: ["skill-21-802-15-4-zigbee-thread-matter-ef24979a81"]
---

## §20. LPWAN and Cellular IoT

```
LoRaWAN   ⚠️ unlicensed sub-GHz, CSS (§10), ~km range, YOU run the gateway.
   ⚠️ No recurring network cost; duty-cycle limited (§23); Class A devices
   only listen briefly after transmitting, so downlink is very constrained
Sigfox    ultra-narrowband, tiny payloads, operator network (⚠️ commercially
   troubled; check viability before designing it in)
NB-IoT    ⚠️ licensed, in-band LTE. Best deep-indoor penetration, lowest
   power, ⚠️ poor mobility, slow FOTA
LTE-M     ⚠️ licensed. Handles MOBILITY, better roaming, enough bandwidth
   for reliable firmware updates, voice capable
LTE Cat-1 / Cat-1 bis  ⚠️ higher rate, very broad availability (§24.2)
5G RedCap ⚠️ "reduced capability" 5G — the mid-tier (§24.2)
NTN       ⚠️ satellite running NB-IoT/LTE-M (§24.2)
```
**⚠️ The decision tree that actually matters** (elaborated in §24.2 → `radio-regulatory-security-and-debugging`):
```
Does it MOVE?              → ⚠️ LTE-M. NB-IoT and LoRaWAN handle mobility poorly
Do you control the site?   → ⚠️ LoRaWAN (no recurring cost) is viable
Data per day?              ⚠️ <1 KB: NB-IoT/LoRaWAN · 1 KB–1 MB: NB-IoT/LTE-M
                             >1 MB: LTE-M or LTE Cat-1
Need reliable OTA updates? → ⚠️ LTE-M. NB-IoT FOTA is slow and painful
No coverage at all?        → NTN/satellite, or LoRaWAN with your own gateway
```

---
