---
id: skill-6-data-pipelines-and-etl-3bb0780c08
purpose: 6 data pipelines and etl
source: src/vibey_tools/skills/plugins/low-code-no-code/skills/lowcode-integration-data-and-app-builders/SKILL.md
requires: ["skill-5-integration-and-ipaas-197b2880bf"]
links: ["skill-7-app-builders-91098e0210"]
---

## §6. Data Pipelines and ETL

| Tool | Position |
|---|---|
| **Alteryx** | ⚠️ **Analyst-facing, desktop-rooted, powerful, expensive.** Strong in finance/insurance analytics. Taken private by Clearlake/Insight in 2024 |
| **Matillion** | Cloud-native ELT, pushdown into the warehouse. Now heavily AI-featured |
| **Talend** (Qlik) | Long-standing, enterprise, broad |
| **Informatica** | The incumbent enterprise ETL |
| **Fivetran / Airbyte** | ⚠️ **Managed EL — extract and load only.** Transformation happens elsewhere |
| **dbt** | ⚠️ **Not low-code — SQL plus engineering practice.** §6.1 |
| **Power Query / Excel** | ⚠️ **The most-used data tool on earth, and the most under-acknowledged** |

### 6.1 ⚠️ The pattern worth internalizing

**[DURABLE] The trajectory in this tier has run the opposite direction to everywhere
else**: the industry moved **from visual ETL toward code-first ELT** — extract and load
cheaply, then transform **in the warehouse with version-controlled SQL**. **dbt's success
is the clearest evidence**, and the reason is instructive: **visual pipelines don't
diff, don't merge, don't review, and don't test well.**

**That is the general low-code weakness stated precisely** — and it's why this is the one
tier where the engineering community broadly moved *away* from the visual paradigm rather
than toward it. **When evaluating any low-code tool, ask: can two people work on this
simultaneously, and can I see what changed?** (§14 → `lowcode-lock-in-and-engineering-practice`)

---
