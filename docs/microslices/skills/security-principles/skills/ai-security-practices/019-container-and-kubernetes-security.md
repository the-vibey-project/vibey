---
id: skill-container-and-kubernetes-security-c9f74b3f20
purpose: container and kubernetes security
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-security-practices/SKILL.md
requires: ["skill-zero-trust-principles-for-ai-systems-30d9023531"]
links: ["skill-observability-for-security-90d8f12867"]
---

## Container and Kubernetes Security

- Run as non-root; read-only filesystem
- Minimal base images (distroless/Chainguard/Alpine)
- Trivy/Checkov scanning in CI
- Egress firewall/allow-list; block cloud-metadata access (IMDSv2, hop limit 1)
- Admission controllers (Kyverno) to require signed images

---
