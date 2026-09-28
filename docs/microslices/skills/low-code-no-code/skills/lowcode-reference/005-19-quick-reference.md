---
id: skill-19-quick-reference-6bc8a12809
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/low-code-no-code/skills/lowcode-reference/SKILL.md
requires: ["skill-18-resources-2205de41e0"]
links: ["skill-20-sources-and-method-4148cbbc09"]
---

## §19. Quick Reference

### 19.1 Tier picker

| Need | Tier / tool |
|---|---|
| Teach programming concepts | Scratch, MakeCode, micro:bit (§2 → `lowcode-landscape-automation-and-ai-generation`) |
| Robotics education, no vendor-retirement risk | ⚠️ **Arduino/Pi/micro:bit over closed kits** (§2.1 → `lowcode-landscape-automation-and-ai-generation`) |
| Connect two SaaS apps | Zapier (easy) / Make (value) / n8n (self-host) (§3 → `lowcode-landscape-automation-and-ai-generation`) |
| Internal automation, self-hosted, developer-owned | n8n — ⚠️ **check the licence** (§3.1 → `lowcode-landscape-automation-and-ai-generation`) |
| Genuinely OSI-licensed automation | Node-RED, Activepieces, Windmill (§3.1 → `lowcode-landscape-automation-and-ai-generation`) |
| Durable, complex, long-running workflows | ⚠️ **Temporal / Airflow — not this category** (§3 → `lowcode-landscape-automation-and-ai-generation`) |
| Prototype an app this afternoon | Lovable / Bolt / v0 / Replit — ⚠️ **then review it** (§4 → `lowcode-landscape-automation-and-ai-generation`) |
| Enterprise system integration | MuleSoft / Boomi / Workato (§5 → `lowcode-integration-data-and-app-builders`) |
| Cloud-native integration, already on a hyperscaler | Logic Apps / Step Functions (§5 → `lowcode-integration-data-and-app-builders`) |
| Move data into a warehouse | Fivetran / Airbyte (§6 → `lowcode-integration-data-and-app-builders`) |
| Transform data in the warehouse | ⚠️ **dbt — code-first, and it wins here** (§6.1 → `lowcode-integration-data-and-app-builders`) |
| Analyst-driven data prep | Alteryx / Matillion / Power Query (§6 → `lowcode-integration-data-and-app-builders`) |
| Internal CRUD tool, 5–500 users | Retool / Power Apps / Budibase (§7 → `lowcode-integration-data-and-app-builders`) |
| Automate a system with no API | RPA — ⚠️ **and plan its retirement** (§8 → `lowcode-integration-data-and-app-builders`) |
| Your core product | ⚠️ **Write code** (§9.2 → `lowcode-adoption-governance-and-security`) |

### 19.2 Before you adopt
- [ ] Which tier is this, actually? (§1 → `lowcode-landscape-automation-and-ai-generation`)
- [ ] Who maintains it when the builder leaves? (§9 → `lowcode-adoption-governance-and-security`)
- [ ] Is it core to the product, or supporting? (§9.2 → `lowcode-adoption-governance-and-security`)
- [ ] **Read the licence** — internal-use restrictions? (§3.1 → `lowcode-landscape-automation-and-ai-generation`, §11 → `lowcode-adoption-governance-and-security`)
- [ ] Cost modelled at 12-month projected volume? (§11 → `lowcode-adoption-governance-and-security`)
- [ ] Can I export the logic in a meaningful form? (§13 → `lowcode-lock-in-and-engineering-practice`)
- [ ] Can I get my data out in bulk? (§13 → `lowcode-lock-in-and-engineering-practice`)
- [ ] What's the vendor's product-retirement history? (§2.1 → `lowcode-landscape-automation-and-ai-generation`, §13 → `lowcode-lock-in-and-engineering-practice`)
- [ ] Dev/test/prod environments available? (§14 → `lowcode-lock-in-and-engineering-practice`)
- [ ] Version control story? (§14 → `lowcode-lock-in-and-engineering-practice`)
- [ ] Where do credentials live, and who can see them? (§12 → `lowcode-adoption-governance-and-security`)
- [ ] **Default visibility on anything AI-generated?** (§4.3 → `lowcode-landscape-automation-and-ai-generation`)
- [ ] Named owner, and a review trigger for graduating to code? (§10 → `lowcode-adoption-governance-and-security`, §13 → `lowcode-lock-in-and-engineering-practice`)

---
