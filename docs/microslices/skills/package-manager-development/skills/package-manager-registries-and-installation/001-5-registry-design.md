---
id: skill-5-registry-design-6ed5b794de
purpose: 5 registry design
source: src/vibey_tools/skills/plugins/package-manager-development/skills/package-manager-registries-and-installation/SKILL.md
requires: []
links: ["skill-6-cache-layout-and-linking-564535a92a"]
---

## §5. Registry Design

### 5.1 The API surface

```
GET  /packages/{name}                  → all versions + metadata (the resolver's hot path)
GET  /packages/{name}/{version}        → one version's metadata
GET  /packages/{name}/{version}/dl     → the artifact (usually a CDN redirect)
POST /packages                         → publish (authenticated)
DELETE / POST /yank                    → yank/unyank (NOT delete — see 5.2)
GET  /search, /index, /changes         → discovery and incremental sync
```
**Design notes that matter at scale:**
- **Separate metadata from artifacts.** Metadata is small, hot, highly cacheable, and
  resolver-critical. Artifacts are large, cold, and belong on a CDN. Conflating them makes
  resolution slow (§3.6 → `package-manager-versioning-and-resolution`).
- **Support conditional requests and incremental sync** (`ETag`, `If-None-Match`, a change
  feed). Mirrors and CI caches depend on it.
- **Paginate and bound everything.** A package with 10,000 versions must not return a
  10 MB JSON blob on every resolution step.
- **Publish upload timestamps** (Python's PEP 700 does) — this is what makes cooldowns
  possible (§8.4 → `package-manager-supply-chain-and-workspaces`).

### 5.2 Immutability — the single most important registry policy

**[DURABLE] A published (name, version) must never change its bytes.** Consequences of
getting this wrong are severe and every ecosystem has learned it, usually the hard way:
- Caches everywhere become incoherent.
- Lockfile integrity hashes break for everyone.
- The `left-pad` incident (2016) — an unpublished package broke thousands of builds —
  established that **unpublishing must be tightly restricted**.

**The correct primitive is a *yank* (or *quarantine*), not a delete:**
- Yanked versions remain downloadable so existing lockfiles keep working.
- They are excluded from *new* resolutions.
- crates.io, PyPI (quarantine), and npm's deprecate/unpublish windows all converge on this.

**⚠️ And immutability has a security cost you must design for:** Go's `proxy.golang.org`
and `sum.golang.org` provide extremely strong reproducibility — but that same immutability
means **a malicious module version, once published and cached, persists and continues to be
served even after the source repository is removed.** Reproducibility and takedown are in
direct tension. Have a documented answer for it.

### 5.3 Mutable-release poisoning — a live design problem

Even with immutable versions, most registries historically allowed **adding new files to an
existing release** (e.g. a new wheel for a new Python version, months later). That's a
poisoning vector: a stolen token lets an attacker add a malicious artifact to a
long-trusted release.

**PyPI closed this in July 2026: new files are rejected on releases older than 14 days.**
The reasoning is instructive — the change was proposed during PEP 740 discussions in
January 2024, stalled, and was revived by the **March 2026 LiteLLM and Telnyx
compromises**. Before shipping, PyPI measured the impact: of the top 15,000 projects, only
**56** had uploaded a Python 3.14-compatible wheel more than 14 days after the release
first appeared. Seth Larson's stated rationale is worth internalizing: it prevents releases
from entering "an indeterminate and confusing state of both compromised and not
compromised, where only a subset of files could be poisoned."

**[DURABLE] That's the template for registry policy changes: identify the vector, measure
the legitimate usage you'd break, publish the numbers, then change the default.**

### 5.4 Namespacing and name allocation

| Model | Example | Trade-off |
|---|---|---|
| Flat, first-come | npm (unscoped), PyPI, crates.io | Simple; **land-grab, typosquatting, permanent name exhaustion** |
| Scoped/namespaced | `@org/pkg` (npm), NuGet prefixes | Ties identity to an owner; reduces squatting |
| Domain-derived | **Go** (`github.com/user/mod`), Maven (reverse-DNS groupId) | Namespace is *inherited from an existing trust root*. Elegant; couples you to the host |
| Content-addressed | Nix, Guix | Names are labels, identity is a hash |

**[DURABLE] Go's and Maven's approach — deriving the namespace from a domain or repo you
already control — eliminates an entire class of problems** (squatting, name disputes,
ownership transfer ambiguity) at the cost of coupling package identity to a hosting
provider. If you're designing new, seriously consider it.

Whatever you choose, you need policy for: name similarity (§8.3 → `package-manager-supply-chain-and-workspaces`), abandoned packages,
ownership transfer, trademark disputes, and reuse of deleted names (**never reuse a name —
that's the "repojacking" attack**).

---
