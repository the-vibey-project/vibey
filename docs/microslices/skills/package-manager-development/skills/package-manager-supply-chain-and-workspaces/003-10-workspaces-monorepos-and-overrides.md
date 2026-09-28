---
id: skill-10-workspaces-monorepos-and-overrides-a610e5e369
purpose: 10 workspaces monorepos and overrides
source: src/vibey_tools/skills/plugins/package-manager-development/skills/package-manager-supply-chain-and-workspaces/SKILL.md
requires: ["skill-9-lifecycle-scripts-and-building-8b40fb61eb"]
links: []
---

## §10. Workspaces, Monorepos, and Overrides

### 10.1 Workspaces

Multiple packages in one repository, resolved together, with local packages satisfying each
other's dependencies instead of the registry.

Requirements that make a workspace implementation good:
- **A single lockfile for the whole workspace.** Per-package lockfiles defeat the purpose.
- **One shared resolution**, so two members can't end up on incompatible versions of a
  shared dependency by accident.
- **An explicit local-link protocol.** pnpm's `workspace:*` **always** resolves to the local
  package — making it impossible to accidentally test against the published version when you
  meant local. That is the correct default and worth copying.
- **Shared version constraints** — pnpm's *catalogs*, Cargo's `[workspace.dependencies]`,
  Maven's `dependencyManagement`. Without this, upgrading a dependency across 50 packages is
  50 edits.
- **Filtering and topological task execution** — `--filter`, run in dependency order.

### 10.2 Non-registry dependencies

Path, git (with a **pinned commit**, never a branch), URL, and vendored dependencies. Each
needs a lockfile representation that preserves reproducibility — a git dependency locked to
a branch name is not locked.

### 10.3 Overrides

`overrides` (npm, pnpm), `resolutions` (Yarn), `[patch]` (Cargo), `replace` (Go).
**[DURABLE] You need this escape hatch** — a transitive dependency has a CVE and the
intermediate package hasn't updated. Design it explicitly rather than letting people
hand-edit lockfiles.

But make it **loud**: overrides silently violate a dependency's declared constraints, which
means you own the compatibility risk. Print them on install. Make them expire or require
periodic re-confirmation if you can.
