---
id: skill-19-test-and-dft-d86b5ec164
purpose: 19 test and dft
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-sequential-timing-metastability-cdc-and-hdl/SKILL.md
requires: ["skill-18-hdl-and-synthesis-14bb09b7b7"]
links: []
---

## §19. Test and DFT

**⚠️ Manufacturing test is not verification** — ⚠️ **verification asks "is the design
right?", test asks "was THIS die made correctly?"**
**⚠️ Fault models**: ⚠️ **stuck-at (the classic), transition/delay faults, bridging — and
ATPG generates patterns against them.**
**⚠️ SCAN CHAINS** are the enabling idea: ⚠️ **connect all flip-flops into a giant shift
register in test mode, so you can load any state and observe any state — converting an
unobservable sequential problem into a tractable combinational one.**
**⚠️ BIST** for memories and logic, ⚠️ **JTAG/boundary scan for board-level test** (see a
peripherals reference §19), ⚠️ **and test compression to keep tester time affordable.**
**⚠️ The cost**: ⚠️ **DFT consumes area and can affect timing, and it is always cheaper than
shipping untestable silicon.**

---

# PART IV — FIRMWARE
