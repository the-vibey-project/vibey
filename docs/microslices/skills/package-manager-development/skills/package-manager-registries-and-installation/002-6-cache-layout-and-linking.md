---
id: skill-6-cache-layout-and-linking-564535a92a
purpose: 6 cache layout and linking
source: src/vibey_tools/skills/plugins/package-manager-development/skills/package-manager-registries-and-installation/SKILL.md
requires: ["skill-5-registry-design-6ed5b794de"]
links: ["skill-7-publishing-and-authentication-40dd8e3b73"]
---

## §6. Cache, Layout, and Linking

### 6.1 The content-addressed store

**[DURABLE] The right shape for a package cache is a global, content-addressed store.**
```
~/.cache/pm/
  index/         metadata, keyed by (name, version), immutable → cacheable forever
  files/         file blobs keyed by content hash (sha256)
  packages/      package trees, assembled from file blobs
  tmp/           staging — assemble here, then atomically rename into place
```
Properties you get for free: deduplication across projects, integrity verification by
construction, safe concurrent access (a hash-named file either exists and is correct, or
doesn't exist), and trivial garbage collection.

**Write atomically**: download to `tmp/`, verify the hash, then `rename()` into place.
A partially-written cache entry that looks complete is the classic "wedged cache" bug that
users fix by deleting the whole cache and cursing your name.

**pnpm's contribution** was demonstrating how much this matters: a single content-addressed
store hard-linked into each project's `node_modules` means one copy of a given package
version on the whole machine, saving developers with many projects tens of gigabytes.

### 6.2 The layout problem — four answers

This is the JavaScript ecosystem's defining argument, and it generalizes.

| Layout | Mechanism | Ecosystem | Trade-off |
|---|---|---|---|
| **Nested** | Each package gets its own `node_modules` | npm v2 | Correct; enormous duplication; Windows path-length failures |
| **Flat / hoisted** | Everything flattened to the top, conflicts nested | npm v3+, Yarn Classic, Bun (default) | Compact, compatible; **allows phantom dependencies** (§6.3) |
| **Isolated / symlinked** | Content-addressed store + hardlinks + a symlink tree mirroring the true graph | **pnpm**, **Bun `--linker isolated`** | Strict — packages can only see what they declared; occasional postinstall scripts assume a hoisted shape and break |
| **No node_modules** | A `.pnp.cjs` map from import to zip archive | **Yarn Berry PnP** | Fastest, strictest, "zero installs"; requires runtime cooperation and breaks tools that stat the filesystem |

> **⚠️ GOTCHA — phantom dependencies are a correctness bug, not a style issue.** Under a
> hoisted layout, `require('lodash')` works even if you never declared lodash, because
> something else hoisted it to the top. Your code then breaks when that transitive
> dependency changes — a failure with no visible cause in your own manifest. Strict layouts
> exist entirely to make this impossible, and **that, not disk space, is their real
> argument.**

**[DURABLE] The generalizable lesson:** you're choosing between *the real dependency graph*
and *a flattened approximation that the runtime finds easier*. Flattening is faster and
more compatible; it is also lying to the program about what it can see. Ecosystems whose
runtime resolution is explicit (Python's `sys.path` per-venv, Cargo's compiler-passed
`--extern`, Go's import paths) never had this problem, because the layout was never the
lookup mechanism.

### 6.3 Multiple versions coexisting

If your runtime can load two versions of the same package simultaneously (npm, Cargo), the
resolver can escape most conflicts (§3.5 → `package-manager-versioning-and-resolution`) — at the cost of duplicated code, larger
artifacts, and **singleton bugs**. If it can't (Python, Java on one classpath), a conflict
is fatal and must be reported, which makes resolution failures far more common and your
error messages far more important.

Cargo's rule is a good middle: **semver-compatible versions are unified into one; semver-
incompatible versions coexist.** This maximizes deduplication while keeping the escape
hatch, and the "expected `foo::Type`, found `foo::Type`" error is the price.

### 6.4 Runtime resolution is part of your design

The package manager's job doesn't end at install; the runtime has to find the code.
- **Node**: directory walk up from the importer, looking for `node_modules` — the reason
  layout *is* resolution.
- **Python**: `sys.path`, one environment per virtualenv — flat, one version of anything.
- **Cargo/Rust**: the compiler is passed explicit `--extern` paths — no filesystem search
  at all, which is why Rust can have two versions of a crate without ambiguity.
- **Go**: import path includes the major version (`/v2`) — **semantic import versioning**,
  so two majors are literally different packages.
- **JVM**: classpath order; first match wins. The source of endless "jar hell."

**[DURABLE] If you're designing a new ecosystem, make runtime resolution explicit and
independent of directory layout.** It removes phantom dependencies, path-length limits,
and hoisting entirely.

---
