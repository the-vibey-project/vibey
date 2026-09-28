---
id: skill-defense-in-depth-e93f580d0c
purpose: defense in depth
source: src/vibey_tools/skills/plugins/security-principles/skills/cybersecurity-principles/SKILL.md
requires: ["skill-zero-trust-philosophy-history-and-what-it-is-not-153984fad2"]
links: ["skill-modern-framework-updates-2024-2026-358ff98161"]
---

## Defense in depth

The insight that no single control is perfect. Borrowed from military castle design — moats, walls, towers, gates — the NSA adapted it for digital systems.

**The fundamental logic**: each layer absorbs failures that breach the previous layer. An attacker who bypasses the perimeter firewall encounters network segmentation. An attacker who compromises one workload encounters microsegmentation. An attacker who escalates privileges is detected by behavioral monitoring. An attacker who exfiltrates data encounters DLP controls.

**Case study — 2024 xz utils backdoor (CVE-2024-3094)**: Organizations with layered defenses detected and contained the supply-chain compromise. Those relying on perimeter security alone were exposed. The attacker executed a sophisticated, patient social engineering campaign targeting a sole burned-out open source maintainer over months to gain commit access. Defense in depth means any single layer failure is recoverable.
