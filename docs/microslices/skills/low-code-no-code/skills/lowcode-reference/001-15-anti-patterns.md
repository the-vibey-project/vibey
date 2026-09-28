---
id: skill-15-anti-patterns-07301b4f77
purpose: 15 anti patterns
source: src/vibey_tools/skills/plugins/low-code-no-code/skills/lowcode-reference/SKILL.md
requires: []
links: ["skill-16-contested-questions-578663929e"]
---

## §15. Anti-Patterns

| Anti-pattern | Why |
|---|---|
| Arguing about "low-code" without saying which tier | Seven categories, one label (§1 → `lowcode-landscape-automation-and-ai-generation`) |
| Building your core differentiator on a platform ceiling | ⚠️ **You inherit someone else's roadmap** (§9.2 → `lowcode-adoption-governance-and-security`) |
| Adopting without asking how to get out | §13 → `lowcode-lock-in-and-engineering-practice`'s five questions |
| Assuming "source available" means open source | ⚠️ **n8n's SUL blocks external-facing commercial use** (§3.1 → `lowcode-landscape-automation-and-ai-generation`) |
| Building a customer-facing product on an internal-use-only licence | ⚠️ **Legal exposure, discovered late** (§3.1 → `lowcode-landscape-automation-and-ai-generation`, §11 → `lowcode-adoption-governance-and-security`) |
| Modelling cost on this month's volume | Per-task pricing is brutal at scale (§11 → `lowcode-adoption-governance-and-security`) |
| Ignoring AI-feature consumption pricing | The fastest-growing surprise line (§11 → `lowcode-adoption-governance-and-security`) |
| **Shipping AI-generated apps without security review** | ⚠️ **~45% contain vulnerabilities; 5,000+ scanned apps had no auth** (§4.3 → `lowcode-landscape-automation-and-ai-generation`) |
| Not checking default project visibility on an AI app builder | ⚠️ **Public by default; 40% of exposed apps leaked sensitive data** (§4.3 → `lowcode-landscape-automation-and-ai-generation`) |
| Treating an AI prototype as production-ready | ⚠️ **"Fastest to production-ready: none"** (§4.3 → `lowcode-landscape-automation-and-ai-generation`) |
| Assuming AI generation replaces citizen development | It doesn't give ops staff a tool they can maintain (§4.2 → `lowcode-landscape-automation-and-ai-generation`) |
| Building directly in production | The biggest quality gap in citizen dev (§14 → `lowcode-lock-in-and-engineering-practice`) |
| No dev/test environment | Same (§14 → `lowcode-lock-in-and-engineering-practice`) |
| Screenshot of a canvas as documentation | ⚠️ **A canvas is not self-documenting** (§14 → `lowcode-lock-in-and-engineering-practice`) |
| No error path, only the happy path | These systems fail constantly (§14 → `lowcode-lock-in-and-engineering-practice`) |
| Assuming exactly-once execution | ⚠️ **They retry. Design idempotent** (§14 → `lowcode-lock-in-and-engineering-practice`) |
| A 200-node visual workflow | Outgrew the tier 170 nodes ago (§3 → `lowcode-landscape-automation-and-ai-generation`, §14 → `lowcode-lock-in-and-engineering-practice`) |
| Visual ETL where dbt would do | ⚠️ **Visual pipelines don't diff, merge, review, or test** (§6.1 → `lowcode-integration-data-and-app-builders`) |
| RPA against a system that has an API | ⚠️ **Automating around a solved problem** (§8 → `lowcode-integration-data-and-app-builders`) |
| Treating RPA as permanent rather than deferred integration | It's deliberate technical debt (§8 → `lowcode-integration-data-and-app-builders`) |
| No inventory of what's deployed | Most orgs can't produce this list (§10 → `lowcode-adoption-governance-and-security`, §12 → `lowcode-adoption-governance-and-security`) |
| Credentials pasted into workflow steps | Centralize secrets (§12 → `lowcode-adoption-governance-and-security`) |
| OAuth scopes granted once by someone who didn't read them | Over-broad, forever (§12 → `lowcode-adoption-governance-and-security`) |
| No offboarding check for orphaned apps | How apps become unowned (§10 → `lowcode-adoption-governance-and-security`) |
| Banning low-code outright | Drives it underground, doesn't stop it (§10 → `lowcode-adoption-governance-and-security`) |
| Allowing everything with no tiering | The 6–18 month problem list (§10 → `lowcode-adoption-governance-and-security`) |
| Adopting a closed education ecosystem without an exit plan | ⚠️ **Mindstorms → SPIKE → CS&AI in four years** (§2.1 → `lowcode-landscape-automation-and-ai-generation`) |
| Quoting Gartner's 75%/80% figures without their definitions | Widely recirculated, rarely defined (§1 → `lowcode-landscape-automation-and-ai-generation`) |

---
