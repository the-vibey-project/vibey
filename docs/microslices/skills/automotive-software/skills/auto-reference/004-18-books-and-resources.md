---
id: skill-18-books-and-resources-090f94313f
purpose: 18 books and resources
source: src/vibey_tools/skills/plugins/automotive-software/skills/auto-reference/SKILL.md
requires: ["skill-17-what-actually-moved-051ec7bf0c"]
links: ["skill-19-quick-reference-a6fd17f4a8"]
---

## §18. Books and Resources

| Source | Why |
|---|---|
| **ISO 26262** (all parts) | ⚠️ **The standard itself. Part 6 is software. Expensive and unavoidable** |
| **ISO 21448 (SOTIF)** | §6.5 → `auto-real-time-safety-and-cybersecurity` |
| **ISO/SAE 21434** | §7.1 → `auto-real-time-safety-and-cybersecurity` |
| **ISO 14229 (UDS)**, ISO 15765, ISO 13400 | §8 → `auto-diagnostics-ota-and-adas` |
| **MISRA C:2012** and **MISRA C++:2023** | §11 → `auto-process-testing-domains-and-supply-chain` |
| **AUTOSAR specifications** | ⚠️ **Free from autosar.org, and enormous. Start with the layered architecture doc** |
| **Ross, *Functional Safety for Road Vehicles*** | ⚠️ **The best readable treatment of ISO 26262** |
| **Smith & Simpson, *Safety Critical Systems Handbook*** | Cross-industry safety engineering |
| **Koopman, *Better Embedded System Software*** | ⚠️ **Practical, and Koopman's automotive safety writing and UA testimony are essential context** |
| **Zimmermann & Schmidgall, *Bussysteme in der Fahrzeugtechnik*** | The bus reference (German) |
| **Corrigan (TI), CAN application notes** | Free, clear, canonical on CAN physical layer |
| **Charette, "This Car Runs on Code"** (IEEE Spectrum) | The scale problem, well told |

**Practical**: **Vector's knowledge base and CAN/AUTOSAR primers** (⚠️ **genuinely good and
free**), **AUTOSAR.org**, **UNECE WP.29 documents** (⚠️ **the regulations themselves are
public — read R155 Annex 5 directly**), **Eclipse SDV**, **COVESA**, **SOAFEE**,
**Automotive SPICE process reference model**, **NHTSA and Euro NCAP** for the
consumer-facing safety regime, and **openpilot / comma.ai** as a reverse-engineered window
into real vehicle bus behaviour.

---
