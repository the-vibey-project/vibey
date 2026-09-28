---
id: skill-17-what-actually-moved-051ec7bf0c
purpose: 17 what actually moved
source: src/vibey_tools/skills/plugins/automotive-software/skills/auto-reference/SKILL.md
requires: ["skill-16-numbers-58df2dbc77"]
links: ["skill-18-books-and-resources-090f94313f"]
---

## §17. What Actually Moved

### 17.1 Regulation — verified August 2026
**⚠️ This is the layer that changed the industry most, and it is not optional.**
- **UN R155 (cybersecurity/CSMS) and R156 (software updates/SUMS)** were **adopted June
  2020**, came **into force January 2021**, and applied **to all new vehicles produced for
  UNECE countries from July 2024.** ⚠️ **Sources vary on phrasing of the intermediate
  dates — the practically important point is that they are fully in effect now.**
- **⚠️ Both require certification by an audited management system**, valid **three years**,
  as a **condition of type approval** across **54+ contracting parties** (EU, UK, Japan,
  South Korea, Australia and others).
- **R155 Annex 5 enumerates 69 attack vectors** that a threat analysis must address.
- **⚠️ Scope is expanding**: reported extension to **Category L (motorcycles, scooters)
  from December 2027.**
- **⚠️ Parallel national frameworks exist** — **China's GB 44495:2024**, described as one
  of the most technically demanding, **effective for new vehicle types from January
  2026** — and India and others are following the UNECE blueprint. **This is no longer a
  European concern.**
- **ISO/SAE 21434 is the engineering standard R155 references**, and ⚠️ **conformance to it
  does not by itself guarantee approval.**

### 17.2 The architectural shift
**⚠️ Zonal is past the decision point and into execution.** Reported 2026 survey data:
**more than 90% of automotive OEMs committed to zonal architecture, with ~80% already
migrating and ~11% with firm plans**; **45% of surveyed OEMs and suppliers rank the SDV
transition as their number one strategic priority.** Named platforms include **VW's SSP**,
**GM Ultifi**, **Mercedes MB.OS**, **BMW's Neue Klasse**, and **Tesla and Rivian** as
existing zonal-principle implementations.

**⚠️ The driver is bandwidth as much as cost**: **CAN FD capped around 8 Mbit/s is
inadequate** for ADAS, high-resolution infotainment and AI cabin features, **accelerating
adoption of 100 Mbit/s to gigabit automotive Ethernet with TSN** (§3.2 → `auto-architecture-buses-and-autosar`).

**AUTOSAR Adaptive** is the middleware answer for HPC nodes — ⚠️ **reported Adaptive
Platform membership growth of 22% in a year, and the Eclipse SDV working group at 50+
members.** **Classic and Adaptive coexist** (§4.2 → `auto-architecture-buses-and-autosar`), with vendor platforms unifying them.

> **⚠️ GOTCHA — treat the market figures above with care.** Adoption percentages, revenue
> forecasts and membership growth come from **analyst reports and vendor-adjacent
> sources**, several of which sell services into this transition. ⚠️ **The direction is
> unambiguous and corroborated across many independent sources; the specific percentages
> are not measurements.** **The engineering content of §2 → `auto-architecture-buses-and-autosar` and §3 → `auto-architecture-buses-and-autosar` does not depend on
> them.**

---
