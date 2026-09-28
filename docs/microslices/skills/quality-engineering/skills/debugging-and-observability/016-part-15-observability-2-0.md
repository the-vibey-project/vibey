---
id: skill-part-15-observability-2-0-23a0133a38
purpose: part 15 observability 2 0
source: src/vibey_tools/skills/plugins/quality-engineering/skills/debugging-and-observability/SKILL.md
requires: ["skill-part-14-customer-issue-triage-e857987992"]
links: ["skill-quick-reference-decision-thresholds-1b12b8a372"]
---

## Part 15 — Observability 2.0

**Charity Majors (Honeycomb)** defines observability via control theory: "the ability to ask any question of your systems — understand any internal state just by observing it from the outside — without having to predict that question in advance." This is about **unknown-unknowns**, requiring **high cardinality and high dimensionality** with no pre-aggregation.

**Observability 1.0:** three pillars (metrics, logs, traces) in separate tools; cost driven by cardinality.

**Observability 2.0:** a single source of truth of **arbitrarily-wide structured events** stored in a columnar database, from which metrics/traces are derived; cost driven by traffic/architecture, scaling with business value. "You can derive metrics from these wide events. And you can't go any other direction."

**Observability-Driven Development (ODD):** engineers design the right logs, metrics, and spans *before* a bug happens. Missing observability is "dark debt." Test that your instrumentation actually emits correctly.

**Caveat:** "Observability 2.0" is a contested framing advanced primarily by Majors/Honeycomb (a vendor with a commercial interest in wide-event tooling). The three-pillars model remains widely and effectively used.

---
