---
id: skill-design-documents-and-rfcs-89d3b74c55
purpose: design documents and rfcs
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-design/SKILL.md
requires: ["skill-the-c4-model-simon-brown-74f8e07a56"]
links: ["skill-architecture-advice-process-6c5ac4a74a"]
---

## Design Documents and RFCs

### When to Write One
Medium+ features (weeks to months of work) where the design involves non-trivial trade-offs, affects multiple teams, or makes hard-to-reverse decisions.

### Industry Practice
Used by Google ("design docs"), Amazon (6-pager / PR-FAQ), Uber (DUCK → RFC → ERD), Stripe, Spotify. The Pragmatic Engineer's research is the best public catalog.

**Key insight (Stedi):** "Writing a doc is not a perfunctory gesture."

### Uber's Scaling Failures (Cautionary)
As RFCs scaled to hundreds weekly:
- Noise: too many RFCs
- Ambiguity: unclear what requires an RFC
- Discoverability: old RFCs hard to find

**Avoid Meta's low-documentation approach** — the Pragmatic Engineer cautions against copying this.

### RFC Structure (Minimal Viable Template)
1. **Problem** — What is being solved and why
2. **Goals / Non-goals** — Explicit scope boundaries
3. **Proposed design** — Options considered, trade-offs, chosen approach
4. **Open questions** — What still needs resolution
5. **Timeline** — Milestones

---
