---
id: skill-13-the-domains-2952fddafb
purpose: 13 the domains
source: src/vibey_tools/skills/plugins/automotive-software/skills/auto-process-testing-domains-and-supply-chain/SKILL.md
requires: ["skill-12-testing-cde13d451c"]
links: ["skill-14-supply-chain-reality-66ae9408db"]
---

## §13. The Domains

| Domain | Typical ASIL | Character |
|---|---|---|
| **Powertrain/propulsion** | C–D | ⚠️ **Hard real-time, crank-synchronous, heavy calibration** |
| **Chassis** (ABS/ESC/steering) | ⚠️ **D** | Fast control loops, fail-operational for by-wire |
| **Body** (lights, doors, HVAC) | QM–B | ⚠️ **Enormous variant complexity, LIN-heavy** |
| **Infotainment** | QM | ⚠️ **Android Automotive / Linux; consumer expectations, automotive lifetime** |
| **ADAS** | B–D | §10 → `auto-diagnostics-ota-and-adas` |
| **Telematics** | QM–B | ⚠️ **The internet-facing attack surface** (§7.3 → `auto-real-time-safety-and-cybersecurity`) |
| **Battery management (EV)** | ⚠️ **C–D** | Cell balancing, SOC/SOH estimation, thermal, contactor control |

**⚠️ Calibration is an automotive-specific concept worth understanding**: powertrain
software ships with thousands of tunable parameters (maps, curves, thresholds) that are
**calibrated per engine/vehicle variant** and stored separately from code. **Calibration
engineers are a distinct discipline**, and ⚠️ **the calibration dataset is often larger and
more valuable than the code.**

**⚠️ Variant handling is a hidden monster**: one platform, dozens of markets, trim levels,
engine options, and regulatory variants. **Preprocessor-driven variant explosion is a real
maintainability crisis**, and feature-model-based configuration is the mitigation.

---
