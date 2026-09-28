---
id: skill-0-routing-f93631263d
purpose: 0 routing
source: src/vibey_tools/skills/plugins/package-manager-development/skills/package-manager-versioning-and-resolution/SKILL.md
requires: []
links: ["skill-1-versions-and-constraints-0e6cc9b259"]
---

## §0. Routing

### 0.1 The anatomy — every package manager has these parts

```
┌──────────────────────────────────────────────────────────────────┐
│ MANIFEST         what the human wrote: deps + constraints        │  package.json, pyproject.toml,
│                  (+ metadata, scripts, workspaces)               │  Cargo.toml, go.mod
├──────────────────────────────────────────────────────────────────┤
│ RESOLVER         constraints + registry metadata → exact versions│  §3
│                  This is the hard part. It is NP-complete.       │
├──────────────────────────────────────────────────────────────────┤
│ LOCKFILE         the resolution, frozen, with integrity hashes   │  §4
├──────────────────────────────────────────────────────────────────┤
│ FETCHER          registry API → tarballs; retries, mirrors, auth │  §5, §7
├──────────────────────────────────────────────────────────────────┤
│ VERIFIER         hashes, signatures, attestations, policy        │  §8
├──────────────────────────────────────────────────────────────────┤
│ CACHE            content-addressed store; global, shared         │  §6
├──────────────────────────────────────────────────────────────────┤
│ LINKER           cache → project layout (copy/hardlink/symlink)  │  §6
├──────────────────────────────────────────────────────────────────┤
│ BUILDER          compile/build native code; run lifecycle scripts│  §9  ← the danger zone
├──────────────────────────────────────────────────────────────────┤
│ RUNTIME RESOLUTION  how the language finds a module at run time  │  §6.4
└──────────────────────────────────────────────────────────────────┘
```

**[DURABLE] These are separable, and separating them is the single best structural
decision you can make.** Resolution should be a pure function of (manifest, registry
metadata) with no I/O side effects, so it is testable, cacheable, and can run offline
against a snapshot. Installation should be a pure function of (lockfile, cache). Package
managers that entangle resolution with fetching and installation are the ones that can't
do `--dry-run`, can't do offline installs, can't produce deterministic lockfiles, and
can't be tested without a network.

### 0.2 The question router

| Asked about... | Go to |
|---|---|
| Version schemes, semver, constraint syntax, ranges | §1 |
| Manifest design, metadata, what to put in it | §2 |
| Resolution algorithms, SAT, PubGrub, MVS, error messages | §3 |
| Lockfiles, reproducibility, integrity hashes | §4 |
| Registry design, APIs, immutability, yanking, mirrors | §5 → `package-manager-registries-and-installation` |
| Caching, install layouts, hardlinks, hoisting, PnP | §6 → `package-manager-registries-and-installation` |
| Publishing, authentication, tokens, trusted publishing | §7 → `package-manager-registries-and-installation` |
| Supply-chain attacks, provenance, Sigstore, SLSA, policy | §8 → `package-manager-supply-chain-and-workspaces` |
| Lifecycle scripts, native builds, sandboxing | §9 → `package-manager-supply-chain-and-workspaces` |
| Workspaces, monorepos, path/git deps, overrides | §10 → `package-manager-supply-chain-and-workspaces` |
| Performance: parallelism, metadata, network | §11 → `package-manager-ux-ecosystems-and-governance` |
| UX: error messages, output, CLI design | §12 → `package-manager-ux-ecosystems-and-governance` |
| Ecosystem comparison table | §13 → `package-manager-ux-ecosystems-and-governance` |
| Governance, funding, deprecation, name squatting | §14 → `package-manager-ux-ecosystems-and-governance` |
| "Don't do this" | §15 → `package-manager-reference` |
| "Which approach is better?" | §16 → `package-manager-reference` (contested) |
| "Is this still current?" | §17 → `package-manager-reference` |
| Books, papers, people | §18 → `package-manager-reference` |

---
