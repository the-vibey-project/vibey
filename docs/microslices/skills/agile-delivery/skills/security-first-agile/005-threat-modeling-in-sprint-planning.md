---
id: skill-threat-modeling-in-sprint-planning-f30f4e68d6
purpose: threat modeling in sprint planning
source: src/vibey_tools/skills/plugins/agile-delivery/skills/security-first-agile/SKILL.md
requires: ["skill-security-definition-of-done-checklist-3a99fcd6fb"]
links: ["skill-security-champions-model-c81407b013"]
---

## Threat Modeling in Sprint Planning

Threat modeling belongs in **backlog refinement**, not as a waterfall gate. Apply a 5–10 minute STRIDE quick-scan per user story when a story introduces new data flows, external integrations, or trust boundary changes. Full models are reserved for epics.

### STRIDE Quick-Scan (per user story, ≤10 min)

| Category | Question | Common Finding |
|---|---|---|
| **Spoofing** | Can someone impersonate a user or service? | JWT validation missing on new endpoint |
| **Tampering** | Can request data be modified in transit or at rest? | Object IDs accepted from client without server-side validation |
| **Repudiation** | Can a user deny performing an action? | No audit trail for admin operations |
| **Information Disclosure** | Does this expose data to unauthorized parties? | API returns sensitive fields the client does not need |
| **Denial of Service** | Can this be abused to exhaust resources? | Unbounded query without pagination |
| **Elevation of Privilege** | Can a lower-privilege user gain higher access? | IDOR — user accesses another user's data by changing an ID parameter |

### When to Use Each Model
- **STRIDE** — per user story during refinement (5–10 min)
- **PASTA** (Process for Attack Simulation and Threat Analysis) — for epics quarterly; 7-stage full methodology
- **MITRE ATT&CK** — for attack simulation and adversary-informed red teaming; map threats to specific techniques (T1190, T1078, T1552, T1059)

### Misuse Stories

Write a misuse story alongside every security-sensitive user story. Format:

> *As a [attacker type], I want to [exploit behavior] by [attack vector], so that I can [attain goal].*
> **Mitigations:** [specific controls] [automated test that proves the mitigation]

Example — Broken Object-Level Authorization:
> *As a malicious authenticated user, I want to access other users' order data by manipulating the orderId parameter in GET /api/orders/{orderId}, so that I can steal PII and financial data.*
> **Mitigations:** Controller verifies `order.UserId == currentUser.Id`. Integration test: authenticated User A requesting User B's order returns 403 Forbidden.

**Security spikes** handle unknowns: time-box 1–3 days. Deliverable is a recommendation and estimated stories, not production code.

---
