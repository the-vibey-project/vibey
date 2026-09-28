---
id: skill-1-the-honest-framing-2a24e726cf
purpose: 1 the honest framing
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-framing-responsibility-identity-and-hierarchy/SKILL.md
requires: ["skill-0-routing-4e43d3db5c"]
links: ["skill-2-shared-responsibility-f384841a8e"]
---

## §1. The Honest Framing

**⚠️ Each cloud has a shape that reflects its origin, and knowing the shape predicts the
service quality better than any comparison matrix.**

```
AWS    ⚠️ Built outward from primitives. The broadest catalogue, the most mature,
       and the most SHARP EDGES. Services are composable and you assemble them.
       ⚠️ Best-in-class breadth; worst-in-class coherence — many services overlap
       and several are effectively legacy but never removed
AZURE  ⚠️ Built inward from enterprise. Deepest integration with Windows, AD,
       Office, and existing enterprise licensing. Strongest hybrid story (Arc,
       Stack). ⚠️ Enterprise agreements and licence portability are often the
       real reason organizations choose it, and that is a legitimate reason
GCP    ⚠️ Built from Google's internal infrastructure. FEWER services, BETTER
       ones in specific areas — BigQuery, GKE, and the network. ⚠️ Historically
       weakest on enterprise sales, support and long-term service commitment,
       which is a real and frequently-cited concern
```
> **⚠️ GOTCHA — the honest selection criteria are rarely technical.** ⚠️ **Existing
> enterprise agreements, what your team already knows, compliance and data residency,
> and which vendor gives you credits usually dominate.** **That is not irrational. The
> technical differences between the three for a typical workload are smaller than the
> difference made by a team that knows the platform.**
> **⚠️ The exceptions where the platform genuinely determines the outcome**: **large-scale
> analytics (BigQuery), Kubernetes at scale (GKE), and Windows/AD-centric estates
> (Azure).**

---
