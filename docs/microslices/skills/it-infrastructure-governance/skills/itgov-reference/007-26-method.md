---
id: skill-26-method-2ea6355ed0
purpose: 26 method
source: src/vibey_tools/skills/plugins/it-infrastructure-governance/skills/itgov-reference/SKILL.md
requires: ["skill-25-quick-reference-762432b464"]
links: []
---

## §26. Method

**§1–§20 → `itgov-infrastructure-layers-compute-storage-and-networking`, `itgov-directory-authentication-authorization-and-privileged-access`, `itgov-identity-lifecycle-access-review-and-segregation-of-duties`, `itgov-endpoints-continuity-itsm-and-vendor-risk` rest on stable material** — **RBAC theory (Ferraiolo, Kuhn & Chandramouli;
NIST SP 800-162), directory and Kerberos fundamentals, Microsoft's tiered administration
model, backup and DR practice, and ITIL/COBIT/NIST CSF process** — sourced from §24.
⚠️ **The joiner-mover-leaver problem, role explosion and rubber-stamped recertification
have been the same three failures for twenty years.**

**Two searches were run in August 2026**, both on identity, **because that is where this
domain actually moved.**

**Confidence.** **High** in §1–§20 → `itgov-infrastructure-layers-compute-storage-and-networking`, `itgov-directory-authentication-authorization-and-privileged-access`, `itgov-identity-lifecycle-access-review-and-segregation-of-duties`, `itgov-endpoints-continuity-itsm-and-vendor-risk`.
**High in §21.1's mechanism and method list** — **the five Entra phishing-resistant
methods, Authentication Strengths, and the Conditional Access enforcement pattern are
consistent across Microsoft Learn documentation and multiple independent practitioners.**
⚠️ **The specific enforcement dates (6 July, 13 July, 7 September 2026) and the September
2026 SMS/voice retirement come from Microsoft release notes as relayed by security press
and community blogs — I'd verify them against current Microsoft documentation before
building a project plan around them, since Microsoft timelines move.**

⚠️ **§21.2 needs the most caution and I've built that into the section rather than
appending it.** **Every commonly cited NHI-to-human ratio — 45:1, 80:1, 100:1, 144:1 —
traces to a vendor selling non-human identity tooling, with the partial exception of
KPMG's Cybersecurity Considerations 2026.** **The methodologies are not comparable and
"identity" is not consistently defined between them.** ⚠️ **I have therefore reported the
range with attribution rather than picking a figure, and stated plainly that the direction
and order of magnitude are what's reliable.** **The same applies to the survey statistics
(92% saying tooling can't manage agent identities), the 17-minute credential exploitation
figure, and the MCP server finding — all indicative, none verified independently, and I've
hedged each in place.**

⚠️ **The mechanism claims in §21.2 I'm confident about on first principles rather than on
the surveys**: **NHIs genuinely cannot do MFA, genuinely don't log out, and genuinely tend
to lack owners.** **Those are structural properties, not survey findings** — **and they're
why the §8 → `itgov-directory-authentication-authorization-and-privileged-access` service-account problem and the agentic-AI problem are the same problem at
different scales.** ⚠️ **The recommendation to eliminate static secrets rather than vault
them is the one I'd stand behind most firmly, because it removes the failure mode instead
of managing it.**
