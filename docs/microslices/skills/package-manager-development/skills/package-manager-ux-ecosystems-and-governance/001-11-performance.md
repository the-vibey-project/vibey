---
id: skill-11-performance-4a14ce8891
purpose: 11 performance
source: src/vibey_tools/skills/plugins/package-manager-development/skills/package-manager-ux-ecosystems-and-governance/SKILL.md
requires: []
links: ["skill-12-ux-42db1816fc"]
---

## §11. Performance

**[DURABLE] The rough cost order, for a cold install:**
```
network metadata round-trips  ≫  artifact download  >  decompression  >  linking  ≫  solving
```
The corollary: **most package managers that are "slow" are network-bound and
serially-bound**, not CPU-bound. uv, Bun, and pnpm's speed comes overwhelmingly from
attacking the first two.

**The techniques that actually matter:**
1. **Parallelism everywhere** — metadata fetch, download, extraction, linking. Bound
   concurrency per-host to avoid being rate-limited.
2. **Metadata-only fetches** — never download an artifact to learn its dependencies (§3.6 → `package-manager-versioning-and-resolution`).
3. **Aggressive, immutable caching** (§5.2 → `package-manager-registries-and-installation` makes this safe) with a global store shared
   across projects.
4. **Hardlink or reflink instead of copy** when populating a project from the store. This
   is often the difference between seconds and minutes for large trees.
5. **Streaming decompression** — extract while downloading.
6. **Skip work**: if the lockfile and the installed tree already agree, do nothing. Fast
   `install` on an up-to-date project should be near-instant.
7. **Write the resolver in a fast language, last.** It's the smallest term.

> **⚠️ On benchmarks.** Published package-manager benchmarks (the widely-circulated 2026
> npm/pnpm/Yarn/Bun comparisons showing e.g. sub-second cold installs for Bun versus ~14 s
> for npm on a 50-dependency project) are single-machine, single-project, and highly
> sensitive to cache state, network, and dependency shape. **The direction is reliable; the
> multipliers are not.** Benchmark your own workload before making an architectural claim.

---
