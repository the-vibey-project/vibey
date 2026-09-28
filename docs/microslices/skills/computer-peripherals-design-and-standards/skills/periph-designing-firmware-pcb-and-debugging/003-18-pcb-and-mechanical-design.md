---
id: skill-18-pcb-and-mechanical-design-60162855c8
purpose: 18 pcb and mechanical design
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-designing-firmware-pcb-and-debugging/SKILL.md
requires: ["skill-17-firmware-b57ef2da16"]
links: ["skill-19-enumeration-and-debugging-5b93883665"]
---

## §18. PCB and Mechanical Design

**⚠️ For USB specifically** (see an electromagnetism reference): ⚠️ **90 Ω differential
impedance for D+/D−, length matching within the pair, avoiding stubs and layer changes on
high-speed pairs, and a continuous ground reference plane under the pair — a split plane
under a differential pair is the classic EMC failure.**
**⚠️ ESD protection on every externally exposed line** — ⚠️ **TVS diodes at the connector,
and this is not optional on a product.**
**⚠️ Power integrity**: ⚠️ **decoupling capacitors close to pins, bulk capacitance,
and a clean supply for analog sections.**
**⚠️ Mechanical**: ⚠️ **connector retention (⚠️ through-hole or reinforced SMD, because a
ripped-off USB connector is the most common physical failure), tolerance stack-up, and
the enclosure process choice — 3D print, injection mould, CNC or sheet metal** (see a
manufacturing reference).
**⚠️ Design for assembly and test** — ⚠️ **test points, and a way to program the board
after assembly.**

---
