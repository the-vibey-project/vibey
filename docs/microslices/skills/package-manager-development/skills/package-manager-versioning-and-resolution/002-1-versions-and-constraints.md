---
id: skill-1-versions-and-constraints-0e6cc9b259
purpose: 1 versions and constraints
source: src/vibey_tools/skills/plugins/package-manager-development/skills/package-manager-versioning-and-resolution/SKILL.md
requires: ["skill-0-routing-f93631263d"]
links: ["skill-2-the-manifest-273a55ce0c"]
---

## §1. Versions and Constraints

### 1.1 Semantic versioning — what it promises and what it delivers

**SemVer** (`MAJOR.MINOR.PATCH[-prerelease][+build]`): MAJOR for breaking changes, MINOR
for backward-compatible features, PATCH for backward-compatible fixes.

**[CONTESTED, with unusually good empirical evidence.]** SemVer is a *social contract*
enforced by nothing, and the research consistently finds it is widely violated:
- A large Maven study found **~20% of non-major upgrades contained breaking changes**,
  though only ~8% of client programs were actually affected.
- Another Java study found a **majority of libraries had at least one syntactically
  breaking patch upgrade**.
- In Rust, a study of **yanked crates.io releases found "breaking SemVer" was the leading
  reason for yanking, at ~43%** — maintainers discovering *after publishing* that they'd
  broken the contract.
- **Hyrum's Law** is the underlying reason: *with a sufficient number of users of an API,
  all observable behaviours of your system will be depended on by somebody* — so even a
  bug fix is a breaking change for someone.

**The strongest critique** (Hynek Schlawack, and the *Software Engineering at Google*
argument) is that SemVer over-predicts breakage — consumers use a small fraction of any
API, so a "major" bump is usually harmless to any given caller — while simultaneously
under-predicting it, because "patch" changes break people via Hyrum's Law. Treating the
version number as a machine-checkable compatibility guarantee is the error; treating it as
a **statement of the author's intent** is correct and useful.

**Design implication for a package manager author:** don't build a system whose safety
depends on SemVer being honoured. Build one where (a) the lockfile is the source of truth,
(b) upgrades are an explicit, reviewable action, and (c) you have a mechanism (yank,
audit, cooldown) for when the contract is broken anyway.

### 1.2 The version scheme decision

| Scheme | Example | Used by | Notes |
|---|---|---|---|
| SemVer | `2.4.1-rc.1+build` | npm, Cargo, Go, most modern | Well-defined precedence; prerelease sorts *before* release |
| PEP 440 | `2!1.4.1rc1.post2.dev3` | Python | **Epochs**, `.postN`, `.devN`, local versions (`+local`). More expressive, harder to implement |
| Debian | `1:2.4.1-3ubuntu2~20.04` | apt | Epoch, upstream version, revision. Comparison rules are genuinely subtle (`~` sorts *before* empty) |
| RPM | `1:2.4.1-3.el9` | dnf/yum | Epoch:Version-Release; `rpmvercmp` |
| Maven | `1.4.1.RELEASE`, `1.4-SNAPSHOT` | Maven | Loose; qualifier ordering is famously surprising |
| CalVer | `2026.8.1` | Ubuntu, pip, some libs | No compatibility claim at all — arguably more honest |

> **⚠️ GOTCHA — prerelease precedence is where implementations disagree.** `1.0.0-alpha`
> < `1.0.0-alpha.1` < `1.0.0-alpha.beta` < `1.0.0-beta` < `1.0.0-rc.1` < `1.0.0`. And
> **prereleases must not satisfy a normal range unless explicitly opted into** — if
> `^1.0.0` matches `2.0.0-alpha.1`, you will ship an alpha to everyone. npm, Cargo, and
> pip all handle this specially, and every naive implementation gets it wrong.

> **⚠️ GOTCHA — version equality vs. normalization.** Is `1.0` the same as `1.0.0`? Is
> `1.0.0+build1` the same as `1.0.0+build2`? (SemVer says build metadata is ignored in
> precedence — so they compare equal, which means a registry must not allow both.) Is
> `1.0.0-RC1` the same as `1.0.0-rc1`? Decide, normalize on ingest, and store the
> normalized form. Ambiguity here becomes a cache-poisoning vector.

### 1.3 Constraint syntax

```
^1.2.3   caret     >=1.2.3 <2.0.0     (npm, Cargo)  ⚠️ For 0.x, ^0.2.3 means >=0.2.3 <0.3.0
~1.2.3   tilde     >=1.2.3 <1.3.0     (npm)         ⚠️ npm ~ and Cargo ~ differ subtly
~=1.2.3  compatible >=1.2.3 <1.3.0    (PEP 440)
1.2.*    wildcard
>=1.2,<2 range
=1.2.3   exact/pin
1.2.3    "1.2.3"   ← MEANS DIFFERENT THINGS: exact in npm, ^1.2.3 in Cargo, minimum in Go
*        any                          ⚠️ crates.io rejects wildcard deps on publish
```

**[DURABLE] Design the constraint language for the *reader*, not the writer.** Every
ecosystem that invented clever operators regrets it. The two decisions that matter:
1. **What does a bare version mean?** Exact, caret, or minimum. This is the highest-traffic
   syntax in your entire system and there is no consensus across ecosystems — pick,
   document loudly, and never change it.
2. **Are ranges allowed at all?** Go says no (§3.4). That single choice removes most of
   the resolver's complexity and most of its usefulness.

---
