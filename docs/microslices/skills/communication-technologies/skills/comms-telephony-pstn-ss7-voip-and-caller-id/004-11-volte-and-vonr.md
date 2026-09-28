---
id: skill-11-volte-and-vonr-9d55e4d667
purpose: 11 volte and vonr
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-telephony-pstn-ss7-voip-and-caller-id/SKILL.md
requires: ["skill-10-voip-and-sip-6a0d7b8a6f"]
links: ["skill-12-caller-id-spoofing-and-robocalls-85e85678f3"]
---

## §11. VoLTE and VoNR

**⚠️ Voice over LTE** carries voice as IP packets over the data network with QoS bearers,
⚠️ **rather than falling back to a circuit-switched network.**
**⚠️ The IMS core** is the architecture underneath, ⚠️ **and it is what makes voice a
service on the data network rather than a separate system.**
**⚠️ The user-visible benefits**: ⚠️ **HD voice via wideband codecs (AMR-WB and EVS),
much faster call setup, and simultaneous voice and data.**
**⚠️ 2G and 3G shutdown** makes VoLTE mandatory rather than optional — ⚠️ **and this has
stranded older handsets and, importantly, a great deal of embedded telemetry** (see a
wireless reference §13).
**⚠️ VoWiFi** uses the same IMS core over any internet connection, ⚠️ **which is why calls
work over hotel Wi-Fi with no coverage, and why emergency location becomes harder** (§27 → `comms-encryption-metadata-interoperability-and-policy`).

---
