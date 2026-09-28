---
id: skill-8-diagnostics-d0352fede1
purpose: 8 diagnostics
source: src/vibey_tools/skills/plugins/automotive-software/skills/auto-diagnostics-ota-and-adas/SKILL.md
requires: []
links: ["skill-9-flashing-and-ota-0e162e1b01"]
---

## §8. Diagnostics

**⚠️ Diagnostics is a huge fraction of real automotive software work and it's invisible
from outside.**

**OBD-II** — legally mandated emissions diagnostics, standardized PIDs and DTCs, the
connector every scan tool uses.
**UDS (ISO 14229)** — the manufacturer diagnostic protocol, and the one you'll implement:
```
0x10  Diagnostic Session Control     ⚠️ default / programming / extended sessions
0x11  ECU Reset
0x14  Clear Diagnostic Information
0x19  Read DTC Information
0x22  Read Data By Identifier        ⚠️ the workhorse — DIDs
0x2E  Write Data By Identifier
0x27  Security Access                ⚠️ seed/key challenge — see the gotcha
0x28  Communication Control
0x2F  Input Output Control By Identifier   ⚠️ actuator tests
0x31  Routine Control
0x34/36/37  Request Download / Transfer Data / Transfer Exit   ⚠️ flashing (§9)
0x3E  Tester Present                 ⚠️ keeps the session alive
```
**Transport**: **ISO-TP (ISO 15765-2)** segments UDS over CAN; **DoIP (ISO 13400)** carries
it over Ethernet/IP — ⚠️ **which is what makes remote and high-speed diagnostics and
flashing practical.**

> **⚠️ GOTCHA — UDS Security Access (0x27) is not security.** The classic implementation is
> a seed/key exchange with a **fixed algorithm shared across a whole vehicle line**, often
> a simple transformation, and **the key material ends up in tester software that gets
> reverse-engineered.** ⚠️ **Treat legacy 0x27 as an interlock against accidents, not as a
> control against an adversary.** Modern practice moves to certificate-based
> authentication and per-ECU credentials — and R155 (§7.2 → `auto-real-time-safety-and-cybersecurity`) is pushing this.

**DTCs**: a code plus **status bits** (test failed, confirmed, pending, ⚠️ **and the
"confirmed" vs "pending" distinction is what stops a single transient setting a warning
lamp**), **freeze frame** data captured at the time of the fault, and **aging/healing**
counters. **⚠️ Debouncing and maturation logic is where diagnostic bugs live** — a fault
that sets too eagerly produces warranty returns for no-fault-found.

---
