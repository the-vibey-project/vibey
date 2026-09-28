---
id: skill-10-migration-a72474a0b5
purpose: 10 migration
source: src/vibey_tools/skills/plugins/cloud-computing/skills/cloud-migration-sovereignty-and-ai-workloads/SKILL.md
requires: []
links: ["skill-11-sovereignty-the-eu-data-act-and-egress-2a3eecc79a"]
---

## §10. Migration

**[DURABLE] The 6 (or 7) Rs, and most organizations pick wrong:**

| Strategy | What | When |
|---|---|---|
| **Rehost** ("lift and shift") | Move as-is | Speed, deadline pressure. ⚠️ **You inherit every existing problem and gain little** |
| **Replatform** | Minor optimizations en route (managed DB, containerize) | ⚠️ **The pragmatic sweet spot for most workloads** |
| **Refactor / re-architect** | Redesign for cloud-native | High value, high cost. Reserve for what earns it |
| **Repurchase** | Move to SaaS | Commodity capability |
| **Retire** | Turn it off | ⚠️ **Consistently underused — a surprising share of any estate is unused** |
| **Retain** | Leave it | Regulatory, or the business case isn't there |
| **Relocate** | Move hypervisor-level | VMware-style bulk moves |

**⚠️ The characteristic mistakes**: lift-and-shift everything then be surprised the bill
went up (you moved a fixed-capacity design onto per-hour billing); **rewriting everything
at once** (see Strangler Fig in a design-patterns reference); **migrating without a
dependency map**; **no rollback plan**; and **treating migration as a project rather than
the start of an operating model change** — which is the one that actually determines
whether it works.

**[DURABLE] Migrate in waves**, starting with something low-risk that teaches you the
operational model, and **measure before and after** so the business case survives contact
with the invoice.

---
