---
id: skill-4-lockfiles-0d030f855d
purpose: 4 lockfiles
source: src/vibey_tools/skills/plugins/package-manager-development/skills/package-manager-versioning-and-resolution/SKILL.md
requires: ["skill-3-dependency-resolution-the-hard-part-d02d370a89"]
links: []
---

## §4. Lockfiles

### 4.1 What a lockfile must contain

```
For each resolved package:
  name, exact version
  INTEGRITY HASH of the artifact           ← the security property
  resolved source (registry URL / git rev / path)
  its dependencies (the resolved edges, not the constraints)
  platform/marker applicability            ← for universal lockfiles
Plus:
  lockfile format version
  a hash of the MANIFEST it was derived from   ← detects "manifest changed, lock is stale"
```

**[DURABLE] The integrity hash is the point.** Without it, a lockfile pins versions but not
*bytes*, and a registry that serves different content for the same version (or a
man-in-the-middle, or a compromised mirror) defeats it entirely. Hash the artifact, and
prefer hashing the *content* rather than the archive where you can, so recompression doesn't
break it.

### 4.2 Design properties that matter

1. **Deterministic serialization.** Sorted keys, stable ordering, consistent formatting.
   A lockfile that produces spurious diffs will not be reviewed, and an unreviewed lockfile
   is a supply-chain hole. (npm's `package-lock.json` reaching 50,000+ lines for large
   projects with noisy diffs is the widely-cited failure of this property.)
2. **Merge-friendliness.** Lockfiles conflict constantly in team workflows. Either make the
   format merge cleanly (flat, per-package, sorted) or ship a merge driver. Most ecosystems
   did the second, late, after years of pain.
3. **Cross-platform validity.** A lockfile generated on macOS must install correctly on
   Linux CI. This requires recording platform-conditional entries rather than only what the
   generating machine needed. uv's universal resolution and Cargo's approach do this;
   `pip freeze` never did, which is why it isn't a lockfile.
4. **Verifiability offline.** `npm ci`, `pip install -r pylock.toml`, `cargo build
   --locked`, `pnpm install --frozen-lockfile` — every ecosystem eventually adds a mode
   that says *install exactly this, fail if the manifest and lock disagree, never resolve*.
   **Build this mode from day one; it is what CI should always use.**

### 4.3 Should libraries commit lockfiles?

**[CONTESTED, and the consensus is more nuanced than the folklore.]**
- The classic rule: *applications commit lockfiles; libraries don't*, because a library's
  lockfile is ignored by consumers and pinning it hides the fact that your declared ranges
  are broken.
- The counter-position, now common: **commit it anyway**, because it makes *your own CI*
  reproducible and lets you bisect. Then add a *separate* CI job that resolves fresh
  (and ideally one that resolves *minimum* versions) to catch range breakage.
- Cargo shipped the modern answer: commit `Cargo.lock` for everything, and it is simply
  ignored when the crate is consumed as a dependency. That removes the trade-off.

### 4.4 The Python standardization story — a case study in lockfile politics

Worth knowing because it illustrates how hard "one lockfile format" is:
- The quest began in **2019**. **PEP 665 was rejected** for being too restrictive (it
  excluded sdists). **PEP 751 went through three complete rewrites** and 1,800+ forum posts
  before acceptance in **March/April 2025**, defining `pylock.toml`.
- Adoption moved fast on the *export* side: pip ≥25.1 (`pip lock`, April 2025), PDM ≥2.24,
  uv ≥0.6.15 all write it. **pip 26.1 (April 2026) added experimental `pip install -r
  pylock.toml`** on the install side.
- **But the flagship tool declined to adopt it as its native format.** uv's author stated
  plainly that `pylock.toml` files "are not sufficient to replace `uv.lock`" — the key
  limitation being that pylock records a fixed marker per package rather than a *graph* of
  dependencies, so it can't express installing an arbitrary subset of the graph. Poetry had
  not shipped support as of April 2026.
- **The durable lesson**: tools with a native lockfile treat a standard format as an
  *export target*, not a replacement, because per-tool lockfiles capture information the
  standard doesn't. Standardizing an interchange format is achievable; standardizing the
  *canonical* format when competing formats are already entrenched is much harder.

> **⚠️ GOTCHA — `pip freeze` and `requirements.txt` are not lockfiles.** No hashes by
> default, no platform markers, no distinction between direct and transitive, no manifest
> linkage. `pip install --require-hashes` gets you partway. Do not design a new system with
> this shape.
