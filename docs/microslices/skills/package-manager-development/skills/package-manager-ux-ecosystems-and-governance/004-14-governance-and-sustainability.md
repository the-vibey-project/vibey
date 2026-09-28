---
id: skill-14-governance-and-sustainability-43da3d92f3
purpose: 14 governance and sustainability
source: src/vibey_tools/skills/plugins/package-manager-development/skills/package-manager-ux-ecosystems-and-governance/SKILL.md
requires: ["skill-13-the-ecosystem-comparison-de9fe14b30"]
links: []
---

## §14. Governance and Sustainability

### 14.1 The registry is critical infrastructure

**[DURABLE] Once an ecosystem depends on you, you cannot go down and you cannot break
compatibility.** Design for: read-path availability via CDN (the registry API being down
should not stop installs of already-known versions), mirrorability, an incremental change
feed, and a documented disaster-recovery story. PyPI's reliance on donated CDN capacity
(Fastly) is typical and worth understanding as a structural fact about how these are funded.

### 14.2 The policies you will need, whether or not you planned them

- **Name disputes, trademark claims, and ownership transfer.**
- **Abandoned packages** — archival/status markers (PyPI's PEP 792 project-status work) are
  better than silence.
- **Deprecation** — a first-class, machine-readable signal, not a README note.
- **Yank vs. delete** (§5.2 → `package-manager-registries-and-installation`) — and the very narrow circumstances for actual removal
  (malware, secrets, illegal content).
- **Malware response** — who can quarantine, how fast, and what users are told.
- **Maintainer burnout and single-maintainer critical packages** — the underlying condition
  behind most account-takeover incidents.

### 14.3 Regulation now reaches package managers

The **EU Cyber Resilience Act** makes vulnerability handling a legal duty for anyone
shipping products with digital elements into the EU — **reporting obligations begin
11 September 2026, full obligations 11 December 2027**. Practical consequences for this
domain:
- **Every dependency is a component in your SBOM**, and its vulnerabilities are your duty
  to handle.
- Package managers are increasingly expected to *emit* SBOMs (`npm sbom --sbom-format
  cyclonedx`) and to make provenance verifiable.
- **CISA guidance requires machine-readable SBOM formats — SPDX or CycloneDX.**
- If you are building a registry or package manager, "we just host files" is no longer a
  tenable position on where your responsibility ends.
