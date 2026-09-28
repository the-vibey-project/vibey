---
id: skill-14-supply-chain-reality-66ae9408db
purpose: 14 supply chain reality
source: src/vibey_tools/skills/plugins/automotive-software/skills/auto-process-testing-domains-and-supply-chain/SKILL.md
requires: ["skill-13-the-domains-2952fddafb"]
links: []
---

## §14. Supply Chain Reality

```
OEM        (VW, Toyota, Ford, GM, Tesla...)  — integrates, owns type approval
Tier 1     (Bosch, Continental, ZF, Denso, Aptiv) — delivers ECUs and systems
Tier 2     silicon, software stacks, tools (NXP, Infineon, Renesas, TI, Vector, EB)
```
**⚠️ The consequences for how you work:**
- **You integrate binaries and configurations you cannot inspect**, with an interface
  contract and a test suite. **Debugging across an organizational boundary is slow.**
- ⚠️ **Requirements flow down and evidence flows up.** Your customer's type approval (§7.2 → `auto-real-time-safety-and-cybersecurity`)
  and ASPICE rating depend on artifacts you produce, which is why documentation demands
  feel disproportionate from inside a supplier.
- **⚠️ The OEM historically owned the architecture and integration, and the Tier-1 owned
  the software.** **The SDV shift is OEMs in-sourcing software** to control the platform —
  which is restructuring the industry and is genuinely contested commercially.
- **New entrants** — NVIDIA, Qualcomm — ⚠️ **supply central compute directly to OEMs,
  bypassing the traditional Tier-1 relationship.**

**⚠️ And the Tesla contrast worth understanding properly**: vertical integration removes
the coordination problem that AUTOSAR exists to solve, which is why a company controlling
its own silicon, architecture and software can move faster. ⚠️ **It does not exempt them
from ISO 26262, R155/R156, or type approval** — the regulatory floor is the same. **The
speed advantage is organizational, not regulatory.**
