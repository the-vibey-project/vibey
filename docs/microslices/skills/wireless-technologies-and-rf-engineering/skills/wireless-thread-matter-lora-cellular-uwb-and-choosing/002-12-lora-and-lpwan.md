---
id: skill-12-lora-and-lpwan-3b01307934
purpose: 12 lora and lpwan
source: src/vibey_tools/skills/plugins/wireless-technologies-and-rf-engineering/skills/wireless-thread-matter-lora-cellular-uwb-and-choosing/SKILL.md
requires: ["skill-11-thread-zigbee-and-matter-fc51ad578a"]
links: ["skill-13-cellular-and-cellular-iot-0507224d7b"]
---

## §12. LoRa and LPWAN

**⚠️ LoRa is the modulation** (⚠️ **chirp spread spectrum — the reason it demodulates
signals BELOW the noise floor, which is genuinely remarkable**); ⚠️ **LoRaWAN is the network
protocol above it.**
**⚠️ The trade is explicit**: ⚠️ **kilometres of range and years of battery, in exchange for
tiny payloads, high latency and very low duty cycle.**
**⚠️ Spreading factor** trades range against airtime — ⚠️ **and higher SF means much longer
transmissions, which consumes duty-cycle allowance and capacity fast.**
**⚠️ Device classes**: ⚠️ **A (uplink-initiated, lowest power), B (scheduled receive slots),
C (continuous receive, mains power).**
**⚠️ Deployment models**: ⚠️ **private gateway versus public network versus roaming — and
the honest question for any LPWAN project is who owns and maintains the gateways.**
**⚠️ The alternatives**: ⚠️ **Sigfox, Wi-Fi HaLow (802.11ah), Amazon Sidewalk, and
cellular NB-IoT/LTE-M** (§13).

---
