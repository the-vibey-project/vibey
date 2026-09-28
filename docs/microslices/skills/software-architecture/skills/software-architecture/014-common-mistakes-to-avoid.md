---
id: skill-common-mistakes-to-avoid-25a04a1937
purpose: common mistakes to avoid
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-architecture/SKILL.md
requires: ["skill-staged-rollout-thresholds-96f6d9d637"]
links: []
---

## Common Mistakes to Avoid
- Premature microservices ("distributed monolith")
- Physical splits without logical splits first
- Copying server data into client stores (fetching into Zustand/Redux)
- `'use client'` at the top of the component tree
- Over-extracting shared packages too early (before a second consumer exists)
- CQRS/event sourcing before understanding the domain
- Renaming/dropping DB columns during rolling deploys
- Relying on Next.js middleware alone for auth (CVE-2025-29927)
- Spoke-to-spoke VNet meshes (bypass hub inspection)
- Mixing Bicep and Terraform on the same resources
- ADRs stored away from code
