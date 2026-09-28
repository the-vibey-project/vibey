---
id: skill-key-caveats-8679b744ae
purpose: key caveats
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-era-security/SKILL.md
requires: ["skill-eu-ai-act-compliance-checklist-cdc9bcd4c9"]
links: []
---

## Key Caveats

- EchoLeak, BodySnatcher, Morris II, and Agent Session Smuggling were disclosed vulnerabilities or researcher PoCs — not confirmed in-the-wild exploitation at time of disclosure
- No single ratified cross-vendor "OAuth-for-agents" standard exists as of mid-2026; agent identity remains fragmented
- The EU AI Act "Digital Omnibus" proposal may defer some high-risk timelines, but plan for Aug 2, 2026
- OWASP labels the Agentic list the "2026" edition though it released December 2025 — same document
- MCP ecosystem vulnerabilities and mitigations are evolving rapidly; re-check current NSA/NIST guidance at implementation time
- Confidential GPU availability (Azure NCC H100 v5) is region- and SKU-limited — verify current availability before architecting
- Vendor self-reported metrics (false-positive reductions, analyst-hours saved) should be validated against independent evaluations (MITRE Engenuity ATT&CK, AV-Comparatives)
