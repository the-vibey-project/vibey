---
id: skill-14-storage-capture-and-everything-else-4fb324bfba
purpose: 14 storage capture and everything else
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-audio-printers-storage-controllers-and-haptics/SKILL.md
requires: ["skill-13-printers-and-scanners-dc0ca49b59"]
links: ["skill-15-controllers-and-haptics-e7d35579b6"]
---

## §14. Storage, Capture and Everything Else

**⚠️ USB Mass Storage versus UASP** — ⚠️ **UASP allows command queuing and is substantially
faster.**
**⚠️ Bridge chips** are the usual culprit in enclosure problems, ⚠️ **including TRIM
passthrough and SMART data being hidden from the host.**
**⚠️ Webcams and capture**: ⚠️ **UVC gives driver-free operation; ⚠️ the bandwidth question
is whether the device does onboard compression (MJPEG, H.264) or sends uncompressed, which
determines what resolutions fit.**
**⚠️ Card readers, docks and hubs** — ⚠️ **and note that a hub SHARES upstream bandwidth,
which is the source of many "my drive got slow when I plugged in the webcam" reports.**

---
