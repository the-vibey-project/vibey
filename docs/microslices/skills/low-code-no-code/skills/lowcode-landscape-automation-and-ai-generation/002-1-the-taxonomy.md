---
id: skill-1-the-taxonomy-a1e31d17be
purpose: 1 the taxonomy
source: src/vibey_tools/skills/plugins/low-code-no-code/skills/lowcode-landscape-automation-and-ai-generation/SKILL.md
requires: ["skill-0-routing-1696da7603"]
links: ["skill-2-education-and-block-based-tools-c07a64b434"]
---

## §1. The Taxonomy

**[DURABLE] The single most useful thing in this document: these are seven different
categories that share a label.** Arguments about "low-code" almost always turn out to be
people talking about different tiers.

| Tier | Examples | Real user | What it replaces |
|---|---|---|---|
| **1. Educational / block-based** | Scratch, MakeCode, Blockly, LEGO, Snap! | Learners | Nothing — it's pedagogy (§2) |
| **2. Workflow automation** | n8n, Zapier, Make, Power Automate | Ops, technical generalists | Glue scripts and cron jobs (§3) |
| **3. AI app generation** | Lovable, Bolt, v0, Replit, Base44 | ⚠️ **63% non-developers** | Prototypes, and increasingly MVPs (§4) |
| **4. Integration / iPaaS** | MuleSoft, Boomi, Workato, Tray | Integration engineers | ⚠️ **Custom middleware — genuinely engineering work** (§5 → `lowcode-integration-data-and-app-builders`) |
| **5. Data pipeline / ETL** | Alteryx, Matillion, Talend, Fivetran, dbt | Analysts, data engineers | SQL scripts and hand-rolled pipelines (§6 → `lowcode-integration-data-and-app-builders`) |
| **6. App builders** | Power Apps, Retool, Bubble, Airtable, Appian | Citizen devs, internal tools teams | Internal CRUD apps (§7 → `lowcode-integration-data-and-app-builders`) |
| **7. RPA** | UiPath, Automation Anywhere, Blue Prism | Process automation teams | ⚠️ **Humans clicking through legacy UIs** (§8 → `lowcode-integration-data-and-app-builders`) |

**[DURABLE] The axis that actually predicts behaviour is not "how much code" — it's
"who maintains it when it breaks at 2am."** Tier 1 nobody; tier 2 the person who built it;
tiers 4–5 a specialist team; tiers 3 and 6 ⚠️ **frequently nobody, which is the governance
problem in §10 → `lowcode-adoption-governance-and-security`.**

**Market context [VERSIONED]**: Gartner's much-quoted projections — **by 2026, 75% of new
enterprise applications built with low-code/no-code (from under 25% in 2020)**, and
**80% of low-code users being outside formal IT (from 60% in 2021)** — with a market
around **$44.5B in 2026**. ⚠️ **Treat these as directional; they are widely recirculated
without their original definitions**, and "application" is doing a lot of work in that
first number.

---
