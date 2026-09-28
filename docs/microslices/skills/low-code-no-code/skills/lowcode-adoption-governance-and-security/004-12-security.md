---
id: skill-12-security-1112bc1cf9
purpose: 12 security
source: src/vibey_tools/skills/plugins/low-code-no-code/skills/lowcode-adoption-governance-and-security/SKILL.md
requires: ["skill-11-licensing-and-cost-traps-7f2c804c01"]
links: []
---

## §12. Security

**[DURABLE] Low-code security failures share a shape: the platform is fine and the
configuration isn't.**

**The recurring issues**: **credentials stored in the platform** (who can see them?),
**over-broad connector permissions** (⚠️ **the OAuth scope granted once, forever, by
someone who didn't read it**), **data leaving your boundary** through a cloud-hosted
runtime, **no audit trail** of who changed what, **injection through user input** into
downstream systems, **⚠️ default-public visibility** (§4.3 → `lowcode-landscape-automation-and-ai-generation`'s finding), and **no dependency
scanning** for embedded custom code.

**⚠️ And the two structural ones**: **the person building has permissions they don't
understand**, and **the security team doesn't know the app exists** (§10).

**Minimum controls**: a **connector allowlist**, **centralized secrets** rather than
credentials pasted into steps, **data-classification enforcement**, **DLP where the
platform supports it**, **audit logging on**, and **⚠️ a scheduled review of what's
actually deployed** — most organizations cannot currently produce that list.
