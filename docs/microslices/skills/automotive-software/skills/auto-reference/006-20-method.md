---
id: skill-20-method-3e9d0a9702
purpose: 20 method
source: src/vibey_tools/skills/plugins/automotive-software/skills/auto-reference/SKILL.md
requires: ["skill-19-quick-reference-a6fd17f4a8"]
links: []
---

## §20. Method

**§1–§6 → `auto-architecture-buses-and-autosar`, `auto-real-time-safety-and-cybersecurity`, §8 → `auto-diagnostics-ota-and-adas`, §9 → `auto-diagnostics-ota-and-adas`, §11–§16 → `auto-process-testing-domains-and-supply-chain` rest on standards and long-stable practice** — **ISO 26262,
ISO 21448, ISO 14229, MISRA, the AUTOSAR specifications, OSEK/VDX, and the CAN
specification** — plus the reference works in §18. ⚠️ **CAN is from 1986, UDS and the ASIL
framework have been stable for over a decade, and the V-model predates all of it. None of
that needed web verification.**

**Scoped to complement**: generic MCU/RTOS/bus material sits in an embedded-IoT reference;
the closest sibling is a flight-software reference, and ⚠️ **§6.4 → `auto-real-time-safety-and-cybersecurity`, §9 → `auto-diagnostics-ota-and-adas` and §12 → `auto-process-testing-domains-and-supply-chain` share
reasoning with it deliberately — safety-critical embedded practice converges across
industries, and the case studies transfer.**

**Two searches were run in August 2026**, confined to the two things that moved:
**the UNECE regulatory layer** and **the zonal/SDV architectural transition.**

**Confidence.** **High** in §1–§6 → `auto-architecture-buses-and-autosar`, `auto-real-time-safety-and-cybersecurity`, §8–§9 → `auto-diagnostics-ota-and-adas` and §11–§14 → `auto-process-testing-domains-and-supply-chain` — standards-based and stable, with the
numbers stated as the standards state them. **High** in §7.2 → `auto-real-time-safety-and-cybersecurity` and §17.1's regulatory
structure: CSMS/SUMS as type-approval conditions, three-year certificate validity, the
69 attack vectors in Annex 5, and R155's relationship to ISO/SAE 21434 are **consistent
across many independent sources including a national approval authority (KBA) and
certification bodies.**

⚠️ **Two deliberate hedges.** **The R155/R156 date sequence is stated inconsistently across
sources** — adoption June 2020, force January 2021, "in force since summer 2022," and
application to all new vehicles from July 2024 all appear. **I have given the sequence with
that caveat rather than asserting one clean timeline; the operationally important fact —
that they are fully in effect and gate type approval — is not in dispute.** ⚠️ **Verify
specific applicability dates for your vehicle category against the UNECE text or your
approval authority.**

**And §17.2's market figures are flagged in place**: adoption percentages, revenue
forecasts and membership growth come from **analyst reports and vendor-adjacent sources
that sell into this transition.** ⚠️ **The direction is corroborated everywhere; the
specific numbers are estimates, not measurements, and none of the engineering content
depends on them.** **§10.4 → `auto-diagnostics-ota-and-adas`'s position — that no accepted sufficient validation methodology
exists for full autonomy — is my assessment, and it is one the industry's own SOTIF
framework implicitly concedes.**
