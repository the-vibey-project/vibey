---
id: skill-3-dependency-resolution-the-hard-part-d02d370a89
purpose: 3 dependency resolution the hard part
source: src/vibey_tools/skills/plugins/package-manager-development/skills/package-manager-versioning-and-resolution/SKILL.md
requires: ["skill-2-the-manifest-273a55ce0c"]
links: ["skill-4-lockfiles-0d030f855d"]
---

## §3. Dependency Resolution — the hard part

### 3.1 The problem, formally

Given a root package's constraints and a universe of package versions each with their own
constraints, find an assignment of exactly one version per selected package such that every
constraint is satisfied and no unreachable package is selected.

**[DURABLE] This is NP-complete.** Di Cosmo et al. proved it in 2005 (the EDOS work) by
encoding 3SAT into Debian and RPM dependency constraints; Russ Cox's "Version SAT" restates
it, and it has been re-proven for other formulations since. The reduction is easy to see:
disjunction is encoded in the *changing dependencies across versions* of a package.

**Why it's tractable in practice anyway:** real dependency graphs are nothing like the
worst case. They're shallow-ish, mostly consistent, and heavily biased toward recent
versions. Every production resolver is an algorithm with terrible worst-case behaviour and
good typical behaviour — plus heuristics and a timeout.

**The canonical hard case, the diamond:**
```
        root
       /    \
   A ^1.0   B ^1.0
      |       |
   D ^1.0   D ^2.0        ← no version of D satisfies both. Now what?
```
The resolver must find a D that satisfies both, prove none exists, or use an escape hatch
(§3.5).

### 3.2 The algorithm families

| Family | How it works | Used by | Trade-off |
|---|---|---|---|
| **Backtracking / DFS** | Try highest version; on conflict, back up and try the next | pip (2020 resolver), Cargo, Swift PM | Simple; exponential worst case; **historically terrible error messages** |
| **Backtracking + forward checking / backjumping** | Prune early, jump past irrelevant choices | Molinillo (Bundler, CocoaPods — Bundler has since moved to PubGrub) | Better pruning, still heuristic |
| **Full SAT / CDCL** | Encode as boolean satisfiability, use a real solver | Composer, **libsolv** (dnf, Conda via libmamba), 0install | Complete and fast; explanations are hard; encoding is fiddly |
| **PubGrub (CDCL specialized for versions)** | Conflict-driven clause learning over version ranges, with derivation tracking | **Dart pub, uv, Poetry (Mixology), Bundler, and the designated replacement for Cargo's solver** | Fast *and* explains failures. The modern default |
| **ASP (Answer Set Programming)** | Declarative, with optimization objectives | **Spack** (via Clingo) | Handles multi-objective optimization (compilers, variants, targets) |
| **Pseudo-Boolean optimization** | SAT + an objective function | Research; some distro tooling | "Best" solution, not just any solution |
| **MVS (Minimal Version Selection)** | No search at all — take the max of the required minimums | **Go modules** | O(graph); trivially reproducible; no ranges |
| **Avoid the problem** | Allow multiple versions to coexist | npm (nesting), Nix/Guix (content-addressed store) | Turns resolution into a layout problem |

### 3.3 PubGrub — why it won

Natalie Weizenbaum designed PubGrub for Dart's `pub` in 2018. Its two contributions:

1. **CDCL over version ranges.** Instead of assigning boolean variables, it works with
   *incompatibilities* — sets of terms that cannot all be true. On conflict it derives a
   *new* incompatibility (clause learning), which prunes an entire region of the search
   space rather than just backing up one step.
2. **The derivation graph is the error message.** Because every incompatibility records
   why it was derived, a failure produces a human-readable proof:
   ```
   Because no versions of foo match >1.0.0 <2.0.0
     and foo 1.0.0 depends on bar ^2.0.0,
     every version of foo requires bar ^2.0.0.
   So, because myapp depends on both foo ^1.0.0 and bar ^3.0.0,
     version solving failed.
   ```
   **[DURABLE] This is the single biggest UX advance in package management in fifteen
   years.** Every prior resolver's failure mode was "could not find a compatible set,"
   which is useless. If you are building a resolver in 2026 and you do not produce an
   explanation, you are shipping a known-solved problem as a known bug.

The Rust `pubgrub` crate is generic over package type (including virtual packages),
version format, and version sets, and lets the caller control prioritization (highest-
versus lowest-version solving) and error rendering. **uv extends it with "forking"** —
splitting the resolution when environment markers (Python version, OS, architecture)
partition the solution space, producing a *universal* lockfile valid across platforms
rather than one lockfile per machine. That extension is the interesting part for anyone
building a cross-platform resolver.

### 3.4 MVS — the radical simplification

Russ Cox's argument for Go modules: most version selection algorithms are overcomplicated.
MVS:
- Modules declare **minimum required versions**, not ranges.
- The build list is: for each module in the graph, **the maximum of all the minimums**
  required by anything in the graph.
- One pass. No backtracking. No SAT. No solver. Deterministic by construction.

**[CONTESTED] MVS's trade-off is the whole argument.**
- *For*: builds are **high-fidelity** — adding a dependency cannot silently upgrade an
  unrelated one, and the result is identical today and in five years without a lockfile.
  It's a dozen lines of pseudocode. There is no resolution failure mode to debug.
- *Against*: you **do not get security patches automatically**. If your dependency requires
  `logrus v1.2.0` and v1.2.1 fixes a CVE, MVS keeps you on v1.2.0 until someone explicitly
  bumps it. Proponents call that a feature (upgrades are deliberate); critics call it a
  security liability at ecosystem scale.
- Note the naming confusion, which appears even in reputable sources: MVS selects the
  **maximum of the required minimums**, which people describe both as "the minimum version
  that satisfies all requirements" and "the highest required version." Both descriptions
  are of the same operation, and the ambiguity causes real misunderstanding.

Go's ecosystem also learned an important lesson the hard way: the original design computed
MVS from a root `go.mod` listing only *direct* dependencies, which meant the file said
`v1.2.3` while the build used `v1.5.0`. Users were endlessly confused and security scanners
couldn't read it statically. **`go mod tidy` and `go get` were changed to write the full
resolved requirement list into the root `go.mod`.** *Lesson: if the manifest doesn't state
the actual answer, tooling and humans will both get it wrong.*

### 3.5 Escape hatches — what to do when there's no solution

| Strategy | Mechanism | Used by |
|---|---|---|
| **Allow multiple versions** | Install both, isolate them | npm (nested `node_modules`), Cargo (multiple semver-major versions coexist), Nix |
| **Version mediation** | Pick one by a rule (nearest-wins, first-declared) | **Maven** — "nearest definition wins," which is deterministic but often surprising |
| **Overrides / resolutions** | User forcibly pins a transitive dep | npm `overrides`, Yarn `resolutions`, pnpm `overrides`, Cargo `[patch]` |
| **Fail loudly** | Report the conflict, make the human decide | pip, Cargo (for same-major conflicts), Bundler |

**[DURABLE] "Allow multiple versions" is not free.** It works for pure, self-contained
libraries. It breaks catastrophically for anything with a *singleton*: a global registry, a
type identity that must be shared, a native library that can only be loaded once, a
database connection pool. That's exactly what peer dependencies exist to express, and why
Rust distinguishes semver-compatible (unified) from semver-incompatible (coexisting) —
and still hits "two versions of the same type, and they're not the same type" errors.

### 3.6 Making resolution fast

The dominant cost is almost never the solver — **it's fetching metadata**. Design for this:

1. **Publish dependency metadata separately from the artifact.** PyPI's historic failure to
   provide dependency metadata via a plain API meant Poetry and pip had to *download and
   unpack sdists* just to learn their dependencies. This is the single largest reason
   Python resolution was slow for a decade. (PEP 658/714 metadata-only fetches fixed much
   of it; uv's speed comes substantially from exploiting them.)
2. **Serve a queryable index**, not one file per package that must be fetched serially.
   Cargo's move from a git index to a **sparse HTTP index** was a large real-world win.
3. **Cache metadata aggressively and immutably** (§5.2 → `package-manager-registries-and-installation` immutability makes this safe).
4. **Prefetch speculatively** — start downloading the versions you're likely to pick while
   still solving.
5. **Bound the search**: prioritize by (fewest versions remaining) then (highest version),
   deprioritize packages with huge version counts, and have a hard timeout with a *useful*
   message rather than an infinite spin.

> **⚠️ GOTCHA — the "backtracking forever" experience.** pip's resolver visibly downloading
> dozens of versions of one package is the canonical user-facing symptom of an unbounded
> backtracking search with expensive metadata access. If your resolver can do this, your
> users will experience it as a hang. Detect it, report which package is thrashing, and
> suggest a narrower constraint.

---
