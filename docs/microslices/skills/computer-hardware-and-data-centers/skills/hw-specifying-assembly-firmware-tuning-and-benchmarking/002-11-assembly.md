---
id: skill-11-assembly-3a83a71026
purpose: 11 assembly
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-specifying-assembly-firmware-tuning-and-benchmarking/SKILL.md
requires: ["skill-10-specifying-a-build-f9e914e585"]
links: ["skill-12-firmware-and-boot-8e5651ffe5"]
---

## §11. Assembly

**⚠️ ESD precautions** (see a cryptography-adjacent electronics reference on static —
⚠️ **high voltage, tiny energy, harmless to you and destructive to semiconductors**): work
on a hard surface, ground yourself, handle boards by the edges.
**⚠️ The order that saves rework**: ⚠️ **CPU, cooler backplate, RAM and M.2 into the board
BEFORE it goes in the case; then PSU; then board; then GPU last.**
**⚠️ The specific care points**: ⚠️ **CPU socket orientation and never touching LGA pins;
⚠️ RAM in the correct slots for dual channel — usually A2/B2, and getting this wrong
halves memory bandwidth silently; ⚠️ standoffs correct and no extras shorting the board;
⚠️ every power connector FULLY seated (§7 → `hw-interconnect-power-thermals-and-networking`); and cable management for airflow.**
**⚠️ Test outside the case first** if anything is uncertain — ⚠️ **it takes minutes and
saves a full disassembly.**

---
