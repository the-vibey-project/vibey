---
id: skill-zero-trust-principles-for-ai-systems-30d9023531
purpose: zero trust principles for ai systems
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-security-practices/SKILL.md
requires: ["skill-ai-threat-modeling-frameworks-6d52cddeff"]
links: ["skill-container-and-kubernetes-security-c9f74b3f20"]
---

## Zero-Trust Principles for AI Systems

- Least-privilege for every actor including **non-human/agent identities**
- Verify explicitly at each layer (don't trust middleware/network position)
- Short-lived scoped credentials for all service-to-service calls
- Per-request authorization at the data layer
- OIDC for CI/CD to cloud (no long-lived secrets)

---
