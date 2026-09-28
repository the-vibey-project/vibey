---
id: skill-20-sources-and-method-6e2756f787
purpose: 20 sources and method
source: src/vibey_tools/skills/plugins/package-manager-development/skills/package-manager-reference/SKILL.md
requires: ["skill-19-quick-reference-bd73541889"]
links: []
---

## §20. Sources and Method

**Method.** Narrative (not systematic) review. Durable material — §1.1 → `package-manager-versioning-and-resolution` (SemVer's empirical
record), §3 → `package-manager-versioning-and-resolution` (resolution theory), §4 → `package-manager-versioning-and-resolution` (lockfile design), §5.2 → `package-manager-registries-and-installation` (immutability), §6 → `package-manager-registries-and-installation` (layout),
§9 → `package-manager-supply-chain-and-workspaces` (install-time execution), §15 (anti-patterns) — is synthesized from the primary
literature, ecosystem specifications, and the canonical writing in §18. Every
**time-sensitive** claim (incidents, versions, dates, adoption figures) was verified
against a primary or near-primary source in **August 2026** and is flagged in §17 with a
decay-risk rating. Where ecosystems have made different defensible choices, §16 presents
both cases rather than adjudicating.

**Search log** (August 2026): npm supply-chain attacks and Shai-Hulud/ChainDrop timeline ·
PEP 751 / pylock.toml adoption and pip 26.1 · PubGrub, SAT, and dependency-resolution
theory · Sigstore / SLSA / provenance adoption across registries · npm vs pnpm vs Yarn vs
Bun layouts and linkers · Go modules, MVS, and the checksum database · PyPI security
posture, PEP 740, trusted publishing, and the 14-day rule · SemVer compliance research and
Hyrum's Law.

**Primary and near-primary sources consulted (selected):**
- **PEPs and PyPA specs** — PEP 740, 751, 807; the `pylock.toml` specification on
  packaging.python.org; pip 26.1 release notes (Richard Si) and changelog
- **Microsoft Security Blog** — "ChainDrop supply chain compromise: anatomy of a
  self-propagating worm" (4 Aug 2026); **JFrog Security Research**; **Unit 42**;
  **Datadog Security Labs** (LiteLLM/telnyx TeamPCP campaign); **ReversingLabs**;
  **Socket**; **Sygnia**
- **GitHub Blog** — "Our plan for a more secure npm supply chain"; "Introducing npm package
  provenance"; **npm docs** on generating provenance statements
- **Sigstore** — project blog (npm provenance GA; cosign verification), community roadmap;
  **SLSA** specification (distributing provenance); **OpenSSF** Securing Software
  Repositories WG
- **PyPI Blog** — 2025 year in review; Help Net Security and contemporaneous reporting on
  the 14-day upload restriction (Seth Larson, Mike Fiedler)
- **go.dev/ref/mod**; **research.swtch.com** (Version SAT, vgo principles)
- **dart-lang/pub** solver documentation; **pubgrub-rs**; **DeepWiki** on uv's resolver
- **Bun documentation** (isolated installs); pnpm documentation
- **Andrew Nesbitt** (`nesbitt.io`) — dependency resolution methods; **ecosyste.ms**
  package-manager-resolvers reference
- Academic: Di Cosmo et al. (EDOS), Maven and Go SemVer-compliance studies, the crates.io
  yanked-releases study, arXiv work on hypergraph dependency resolution

**Confidence statement.** **High confidence** in §1–§7 → `package-manager-versioning-and-resolution`, `package-manager-registries-and-installation`, §9–§12 → `package-manager-supply-chain-and-workspaces`, `package-manager-ux-ecosystems-and-governance`, §15, §18–§19 — these rest
on specifications, primary ecosystem documentation, and peer-reviewed or widely-replicated
research. **High confidence** in §17's verified items as of the stated date.
**Moderate confidence** in §8 → `package-manager-supply-chain-and-workspaces`'s incident specifics and §11 → `package-manager-ux-ecosystems-and-governance`'s performance figures: the
attack narratives come from security-vendor research with commercial incentives and were
cross-read across multiple independent vendors (Microsoft, JFrog, Unit 42, Datadog, Socket,
ReversingLabs) where possible, but package counts and detection latencies are
vendor-measured and vary between reports; the package-manager benchmark figures are
single-machine and single-project and are flagged in place as directional only. The
"7-day cooldown would have prevented 8 of 10 attacks" figure is reported alongside the pip
26.1 release and is repeated here with its source named — it is a compelling result from a
single analysis, not an established measurement.
