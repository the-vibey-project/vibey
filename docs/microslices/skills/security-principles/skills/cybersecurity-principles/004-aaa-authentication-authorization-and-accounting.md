---
id: skill-aaa-authentication-authorization-and-accounting-7fe93cb775
purpose: aaa authentication authorization and accounting
source: src/vibey_tools/skills/plugins/security-principles/skills/cybersecurity-principles/SKILL.md
requires: ["skill-the-cia-triad-what-security-protects-2f84706f8a"]
links: ["skill-zero-trust-philosophy-history-and-what-it-is-not-153984fad2"]
---

## AAA: Authentication, Authorization, and Accounting

The lifecycle of any access decision. The three are inseparable.

**Authentication**: establishes identity — "who are you?" Knowledge (password), possession (hardware token), inherence (biometric). Multi-factor combines categories so compromising any single factor is insufficient.

**Authorization**: determines permissions — "what can you do?" Requires authentication first — authorization without authentication is unverifiable.

**Accounting**: creates an audit trail — "what did you do?" Without accounting, you cannot detect or prove abuse. Authentication without accounting leaves you unable to reconstruct what happened after an incident.

**Non-repudiation**: a property enabled by accounting — the signer cannot deny having signed, the actor cannot deny having acted. Digital signatures provide non-repudiation. Under the EU's eIDAS Regulation, Qualified Electronic Signatures have legal equivalence to handwritten signatures.
