---
id: skill-5-integration-and-ipaas-197b2880bf
purpose: 5 integration and ipaas
source: src/vibey_tools/skills/plugins/low-code-no-code/skills/lowcode-integration-data-and-app-builders/SKILL.md
requires: []
links: ["skill-6-data-pipelines-and-etl-3bb0780c08"]
---

## §5. Integration and iPaaS

**[DURABLE] The most genuinely engineering-shaped tier, and the one most misrepresented as
"no-code."**

**MuleSoft** (Salesforce) — Anypoint Platform, API-led connectivity, ⚠️ **expensive and
genuinely powerful; a real skill set, not a citizen-developer tool.**
**Boomi** — cloud-native iPaaS, strong mid-market position.
**Workato** — ⚠️ **the most "modern" feeling; strong on business-user accessibility with
real governance.**
**Tray.ai**, **Celigo**, **Jitterbit**, **SnapLogic**, **Azure Logic Apps** (⚠️ **the
Azure-native answer, and cheap if you're already there**), **AWS Step Functions +
EventBridge** (⚠️ **code-first, and usually the better answer inside AWS**).

**[DURABLE] What this tier is actually for**: connecting systems that don't want to be
connected — SAP to Salesforce, mainframe to modern API, on-prem to cloud — with
**transformation, error handling, retries, monitoring, and governance** as first-class
concerns. **The value is the connector library and the operational layer, not the visual
editor.**

**⚠️ The patterns still apply.** Everything a design-patterns reference says about the
dual-write problem, sagas, idempotency, and at-least-once delivery is **exactly as true
inside an iPaaS canvas** — and easier to get wrong, because the canvas makes a
distributed transaction look like a flowchart.

---
