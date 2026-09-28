---
id: skill-building-the-mental-model-the-threat-landscape-b0d2fc1d3e
purpose: building the mental model the threat landscape
source: src/vibey_tools/skills/plugins/security-principles/skills/cybersecurity-principles/SKILL.md
requires: ["skill-financial-context-why-principles-violations-are-expensive-8a52bf8367"]
links: ["skill-ai-era-relevance-bb9f736e95"]
---

## Building the mental model: the threat landscape

### The structural asymmetries

**Cost asymmetry**: a DDoS attack costs approximately $38/hour to launch but $40,000/hour for victims to defend — a 1,000× cost asymmetry. Attackers win economically.

**Prosecution risk**: estimated 0.05% in the US (WEF 2020). The economic incentives heavily favor attackers.

**Attacker's advantage**: defenders must protect everything; attackers need only one weakness. This asymmetry is irreducible and should inform defensive strategy — assume breach and invest heavily in detection and response, not just prevention.

### How most breaches actually happen

**Verizon 2024 DBIR**: 68% of breaches involve a non-malicious human element. Social engineering exploits authority, urgency, social proof, and reciprocity — bypassing technical controls entirely.

**Verizon 2025 DBIR**: third-party involvement in breaches doubled to 30% year-over-year. You cannot outsource accountability — when a vendor is breached, you bear the consequences.

**Credential abuse** is the most common initial access vector: 22% of all breaches, 88% of basic web application attacks.

### Memory safety: the dominant vulnerability class

Microsoft revealed ~70% of all CVEs from 2006-2018 were memory safety issues. Google Chromium reports the same figure. Google Project Zero found 67% of zero-day exploits in 2021 targeted memory safety bugs. NSA and CISA jointly recommended transitioning to memory-safe languages (Rust, Go, Java, C#, Swift) in 2023.
