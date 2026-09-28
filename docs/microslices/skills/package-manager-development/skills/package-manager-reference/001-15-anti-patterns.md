---
id: skill-15-anti-patterns-eb011c3bf1
purpose: 15 anti patterns
source: src/vibey_tools/skills/plugins/package-manager-development/skills/package-manager-reference/SKILL.md
requires: []
links: ["skill-16-contested-questions-29c2831a7b"]
---

## §15. Anti-Patterns

| Anti-pattern | Why | Instead |
|---|---|---|
| No lockfile | Unreproducible builds; every install is a new resolution | Lockfile with integrity hashes, from v1 |
| Lockfile without hashes | Pins versions, not bytes | sha256/sha512 per artifact |
| Lockfile that only works on the generating platform | CI breaks | Universal/marker-aware lockfiles (§4.2 → `package-manager-versioning-and-resolution`) |
| Resolving in CI | Non-reproducible, and installs today's malware | `ci`/`--frozen-lockfile`/`--locked` |
| Running install scripts by default | The primary malware vector (§9 → `package-manager-supply-chain-and-workspaces`) | Default off + allowlist |
| Mutable published versions | Cache incoherence, hash breakage | Immutable + yank (§5.2 → `package-manager-registries-and-installation`) |
| Allowing new files on old releases | Retroactive poisoning | Time-bounded (§5.3 → `package-manager-registries-and-installation`) |
| Reusing deleted package names | Repojacking | Never reuse |
| Long-lived publish tokens | Harvest-now-use-later; worm fuel | Trusted publishing / OIDC (§7.1 → `package-manager-registries-and-installation`) |
| Trusting by org or `*` in trusted publishing | Looks secure, isn't | Full repo + branch/environment |
| Pinning CI actions by tag | Mutable reference; root cause of 2026 incidents | Pin by commit SHA |
| Requiring artifact download to learn dependencies | Resolution is now network-bound and slow | Metadata-only endpoints |
| Resolver that discards its derivation | Unfixably bad error messages | PubGrub-style incompatibility tracking |
| Unbounded backtracking with no diagnostics | Users experience a hang | Bound, and report what's thrashing |
| Non-deterministic lockfile serialization | Spurious diffs → unreviewed lockfiles | Sorted, stable output |
| Entangling resolve / fetch / install | No dry-run, no offline, untestable | Separate the stages (§0.1 → `package-manager-versioning-and-resolution`) |
| Non-atomic cache writes | Wedged caches users fix by `rm -rf` | Stage + verify + rename |
| Flat/hoisted layout with no strict option | Phantom dependencies | Offer an isolated linker |
| Letting a public index satisfy a private name | Dependency confusion | Scope-pinned registries |
| Treating SemVer as a guarantee | It's violated at measurable rates (§1.1 → `package-manager-versioning-and-resolution`) | Lockfile is truth; upgrades are explicit |
| Hand-editing a lockfile | Always a bug | Provide `overrides` (§10.3 → `package-manager-supply-chain-and-workspaces`) |
| No `why`/`explain` command | Users cannot debug their own tree | Ship it early |
| Delete-on-request unpublish | `left-pad` | Yank |

---
