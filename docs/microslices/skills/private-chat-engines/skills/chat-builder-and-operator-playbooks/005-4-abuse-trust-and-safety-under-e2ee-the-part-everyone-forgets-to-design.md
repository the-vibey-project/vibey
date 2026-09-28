---
id: skill-4-abuse-trust-and-safety-under-e2ee-the-part-everyone-forgets-to-design-6d5499f734
purpose: 4 abuse trust and safety under e2ee the part everyone forgets to design
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-builder-and-operator-playbooks/SKILL.md
requires: ["skill-3-the-metadata-budget-every-service-must-fill-this-table-5dc70bdbf5"]
links: ["skill-5-the-unglamorous-80-b86b84f9aa"]
---

## 4. Abuse & trust-and-safety under E2EE (the part everyone forgets to design)

- **Report flows that carry evidence**: WhatsApp-style "forward last N messages with the report";
  **message franking** (HMAC-style cryptographic "the server really relayed this content"
  receipts) appears in MIMI drafts and Meta's E2EE design.
- **Rate limits without content**: sealed-sender tokens, anonymous credentials for action
  budgets ("N group joins/day, unlinkable").
- **Spam in identifier-free systems** is genuinely hard: SimpleX and Session push burden onto
  link-exchange UX; Signal uses phone-number economics; expect to invent little else.
- **Client-side scanning (Chat Control design space)** is technically "upload moderation" and is
  the policy attack surface right now; decide your policy *before* the law decides it for you
  (Signal's/Element's answer: leave the market; Meta's answer for unencrypted tiers: scan).
- **Ephemeral media safety**: perceptual hashing on-server fails under E2EE by construction; if
  you promise regulators anything else you are writing fiction.
