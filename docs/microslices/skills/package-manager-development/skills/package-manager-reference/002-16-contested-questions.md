---
id: skill-16-contested-questions-29c2831a7b
purpose: 16 contested questions
source: src/vibey_tools/skills/plugins/package-manager-development/skills/package-manager-reference/SKILL.md
requires: ["skill-15-anti-patterns-eb011c3bf1"]
links: ["skill-17-currency-snapshot-verified-august-2026-2433908836"]
---

## §16. Contested Questions

**16.1 MVS vs. constraint solving.** §3.4 → `package-manager-versioning-and-resolution`. Determinism and simplicity versus automatic
patch adoption and expressiveness. Note this is genuinely unresolved: Go's ecosystem is
happy, and the rest of the world independently chose the other way.

**16.2 Should multiple versions coexist?** §6.3 → `package-manager-registries-and-installation`. Compatibility and resolvability versus
duplication and singleton bugs. Language runtime capability largely decides this for you.

**16.3 Hoisted vs. isolated vs. PnP.** §6.2 → `package-manager-registries-and-installation`. Compatibility versus correctness. The
phantom-dependency argument is the strongest technical case for strictness; the volume of
postinstall scripts that assume a hoisted shape is the strongest case against.

**16.4 Lockfiles for libraries.** §4.3 → `package-manager-versioning-and-resolution`.

**16.5 One standard lockfile format vs. per-tool formats.** §4.4 → `package-manager-versioning-and-resolution`. The Python experience
suggests standard-as-interchange is achievable, standard-as-canonical is not, once
competing formats have shipped.

**16.6 Is SemVer worth it?** §1.1 → `package-manager-versioning-and-resolution`. The empirical violation rates are not in dispute; what's
disputed is whether an imperfect declared intent beats no signal at all. (Most people who
say "SemVer doesn't work" still want maintainers to use it.)

**16.7 Should the package manager also be the build tool?** Cargo and Bun say yes
(integration, one config, coherent caching). npm/pip historically say no (separation of
concerns, competing build tools can innovate). Integration wins on UX and loses on
flexibility; both camps ship successful tools.

**16.8 Cooldowns: safety vs. patch latency.** §8.4 → `package-manager-supply-chain-and-workspaces`. The 8-in-10 prevention figure is
striking; the counter is that a cooldown also delays the fix for the *next* incident.
Nobody has a clean answer to "how do you expedite genuine security patches through a
cooldown" that doesn't reintroduce the attack surface.

**16.9 Vendoring.** Vendored dependencies give you total control, auditability, and
immunity to registry outages and takedowns — at the cost of enormous repos and manual
security updates. Go supports it first-class; most ecosystems treat it as a last resort.
Both positions are held by serious organizations.

---
