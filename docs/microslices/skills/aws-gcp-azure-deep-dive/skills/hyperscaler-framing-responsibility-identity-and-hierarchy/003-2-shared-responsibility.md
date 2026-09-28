---
id: skill-2-shared-responsibility-f384841a8e
purpose: 2 shared responsibility
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-framing-responsibility-identity-and-hierarchy/SKILL.md
requires: ["skill-1-the-honest-framing-2a24e726cf"]
links: ["skill-3-identity-and-access-where-they-genuinely-differ-a654d76446"]
---

## §2. Shared Responsibility

**⚠️ The provider secures the cloud; you secure what you put in it.** **The line moves by
service model**, and ⚠️ **misunderstanding where it sits is the root cause of most cloud
breaches** — **which are overwhelmingly customer-side misconfiguration, not provider
compromise.**
```
IaaS   ⚠️ You: OS, patching, network config, IAM, data, application
PaaS   ⚠️ You: IAM, data, application config
SaaS   ⚠️ You: IAM, data, and usage
ALWAYS YOURS, on every model: ⚠️ identity, access policy, data classification,
       and the correctness of your configuration
```
**⚠️ The canonical failure is a publicly-readable object store bucket.** **All three
providers now default to private and warn loudly, and it still happens** — because
⚠️ **someone made it public deliberately to solve a problem and never reverted it.**

---
