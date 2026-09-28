---
id: skill-13-cellular-and-cellular-iot-0507224d7b
purpose: 13 cellular and cellular iot
source: src/vibey_tools/skills/plugins/wireless-technologies-and-rf-engineering/skills/wireless-thread-matter-lora-cellular-uwb-and-choosing/SKILL.md
requires: ["skill-12-lora-and-lpwan-3b01307934"]
links: ["skill-14-uwb-cf2d31e040"]
---

## §13. Cellular and Cellular IoT

**⚠️ The generations**: ⚠️ **and note 2G/3G SUNSET has stranded a great deal of deployed
telemetry — a live lesson about designing hardware around a network you don't control.**
**⚠️ 5G's three service classes** are the useful framing: ⚠️ **eMBB (bandwidth), URLLC
(latency and reliability), mMTC (device density) — and no deployment delivers all three at
once.**
**⚠️ mmWave versus sub-6 GHz** is §2 → `wireless-propagation-link-budget-modulation-antennas-and-spectrum`'s physics again: ⚠️ **enormous bandwidth, terrible
propagation and building penetration, which is why mmWave coverage is patchy and sub-6 does
the real work.**
**⚠️ For IoT specifically**: ⚠️ **NB-IoT (deep indoor penetration, tiny data) and LTE-M
(more bandwidth, mobility, VoLTE) — with PSM and eDRX as the power-saving mechanisms that
make multi-year battery life possible on a cellular radio.**
**⚠️ Practical concerns**: ⚠️ **eSIM/iSIM provisioning, roaming agreements and permanent
roaming restrictions, module certification against carrier requirements (⚠️ which is
separate from and additional to regulatory certification, §18 → `wireless-antenna-integration-certification-low-power-and-debugging`), and network sunset risk.**

---
