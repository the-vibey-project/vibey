---
id: skill-practical-stride-in-agile-sprints-a8bb621a6a
purpose: practical stride in agile sprints
source: src/vibey_tools/skills/plugins/security-principles/skills/threat-modeling-playbook/SKILL.md
requires: ["skill-mitre-att-ck-intelligence-driven-threat-modeling-b495d5d542"]
links: ["skill-full-threat-model-document-structure-ce10b37165"]
---

## Practical STRIDE in Agile sprints

For teams that need threat modeling at development velocity, not just at architecture-review time:

**Lightweight STRIDE per user story (5-10 minutes)**:

1. Draw the trust boundary around the story: what inputs come from outside this boundary?
2. Apply only relevant STRIDE categories (not all six every time):
   - User input involved? → Spoofing, Tampering, Elevation of Privilege
   - Sensitive data stored or transmitted? → Information Disclosure
   - External calls made? → Spoofing, Tampering
   - Resource-intensive operation? → Denial of Service
3. For each confirmed threat, create a **misuse story**: "As an attacker, I want to [threat] so that I can [impact]."
4. Add confirmed threats to the security backlog as acceptance criteria or separate security stories.

**Misuse story format**:
```
As a [type of attacker],
I want to [specific attack action],
So that I can [business impact].

Mitigation: [specific control to add/verify]
Acceptance Criteria: [how to verify the mitigation works]
```

Example misuse story:
```
As an unauthenticated external attacker,
I want to enumerate valid usernames by observing different response times for 
  existing vs non-existing accounts during login,
So that I can reduce the search space for a credential stuffing attack.

Mitigation: Constant-time comparison for all authentication responses regardless 
  of whether the username exists.
Acceptance Criteria: Response time variance between valid/invalid usernames 
  is < 5ms under load testing.
```
