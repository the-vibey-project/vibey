---
id: skill-13-multiple-access-cff0c792f0
purpose: 13 multiple access
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-spread-spectrum-ofdm-access-and-sdr/SKILL.md
requires: ["skill-12-coding-and-retransmission-1bc572f0c9"]
links: ["skill-14-sdr-and-iq-sampling-6577dfeb0e"]
---

## §13. Multiple Access

```
FDMA / TDMA / CDMA / OFDMA / SDMA   ⚠️ divide by frequency, time, code,
   subcarrier, or space (beamforming/MIMO)
⚠️ CSMA/CA   listen before transmit, random backoff — Wi-Fi. ⚠️ Note
   CSMA/CD (collision DETECTION, from Ethernet) is IMPOSSIBLE on radio:
   you cannot hear a collision while transmitting
ALOHA        ⚠️ just transmit and hope. LoRaWAN. Simple; capacity collapses
   under load — classic ALOHA tops out around 18% channel utilization
```
> **⚠️ GOTCHA — the hidden node problem is the classic wireless-only failure and it has
> no wired analogue.** ⚠️ **A and C can both hear B but not each other, so both sense the
> channel as clear and both transmit, colliding at B.** **Carrier sensing cannot fix
> this** — **RTS/CTS can, at a cost in overhead.** **Symptom: throughput collapses when a
> particular pair of nodes is active, and each node's local view looks fine.**

---

# PART II — SOFTWARE-DEFINED RADIO

---
