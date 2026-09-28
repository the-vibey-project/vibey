---
id: skill-1-what-makes-it-different-b38eb12c4f
purpose: 1 what makes it different
source: src/vibey_tools/skills/plugins/automotive-software/skills/auto-architecture-buses-and-autosar/SKILL.md
requires: ["skill-0-routing-52e5ba424c"]
links: ["skill-2-e-e-architecture-71d8441289"]
---

## §1. What Makes It Different

| Constraint | Consequence |
|---|---|
| **Safety-critical** | ⚠️ **ASIL drives architecture, not the other way round** (§6 → `auto-real-time-safety-and-cybersecurity`) |
| **Hard real-time** | Deadlines are physical — a late airbag decision is a failure (§5 → `auto-real-time-safety-and-cybersecurity`) |
| **15+ year lifetime** | ⚠️ **Toolchain, parts and people all outlive the project** |
| **Extreme cost pressure** | ⚠️ **Cents matter at 500k units. This is why 8-bit MCUs persist** |
| **Harsh environment** | −40 to +125 °C, vibration, EMI, 12 V transients (§16 → `auto-reference`) |
| **Supply chain built** | ⚠️ **You integrate binaries you cannot inspect** (§14 → `auto-process-testing-domains-and-supply-chain`) |
| **Regulated type approval** | ⚠️ **You cannot sell without it, and now that includes software** (§7 → `auto-real-time-safety-and-cybersecurity`) |
| **Recalls are catastrophic** | Millions of units, physical service, reputational damage |

**⚠️ The cultural inversion for someone from web or cloud**: **there is no "roll forward."**
Historically there was no rolling anything — the software shipped in the car and stayed.
**OTA changed that, but conservatively**: a staged, signed, approved, rollback-capable
campaign (§9 → `auto-diagnostics-ota-and-adas`), not a continuous deployment pipeline.

**⚠️ And the honest tension in the industry right now**: Tesla demonstrated that a vehicle
could be treated as a software platform with frequent updates and centralized compute, and
the rest of the industry is restructuring to match — **while carrying legacy architecture,
a supply chain built around distributed ECUs, and type-approval obligations that a
software-first company also has to meet** (§17.2 → `auto-reference`).

---
