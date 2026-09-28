---
id: skill-16-contested-questions-498f11528f
purpose: 16 contested questions
source: src/vibey_tools/skills/plugins/web-browser-development/skills/browser-development-reference/SKILL.md
requires: ["skill-15-anti-patterns-3170c11eb6"]
links: ["skill-17-currency-snapshot-verified-august-2026-b66e4fe7f9"]
---

## §16. Contested Questions

**16.1 Manifest V3.** §10.2 → `browser-extensions-platform-and-standards`. Real security argument; real conflict of interest; Firefox
demonstrating that supporting both is technically possible.

**16.2 Capability APIs — how much should the web be able to do?** §11 → `browser-extensions-platform-and-standards`. Chrome's "the web
should match native" versus Apple's and Mozilla's "every API is attack surface and
fingerprinting entropy." Both coherent; the disagreement is about risk appetite and,
inescapably, about business models.

**16.3 The engine monoculture.** *For consolidation*: one excellent open-source engine
beats five mediocre ones; interop problems vanish. *Against*: 81% share means one vendor's
priorities become web policy, "works in Chrome" replaces "follows the spec," and there's no
check on capability expansion. Note that the counterweight is weakening — Gecko is at ~3%
and Mozilla's revenue depends largely on a Google search deal.

**16.4 Site Isolation's cost.** §2.2 → `browser-engine-architecture-and-networking`. Chromium's own docs concede the process-count ceiling,
especially on Android. The emerging answer is memory-safe languages buying back the
isolation that processes were paying for.

**16.5 JIT or no JIT.** §7.1 → `browser-rendering-pipeline`. Ladybird's no-JIT position and Apple's JIT entitlement
restrictions on iOS come from the same reasoning: JITs are enormous exploit surfaces.
The cost is performance, and nobody has shown a no-JIT engine that's competitive on
JS-heavy sites.

**16.6 Fingerprinting: randomize or uniformize.** §9.3 → `browser-security-and-privacy`.

**16.7 Should the browser block ads by default?** Brave does; others don't. It's a
security control (malvertising), a privacy control, and an existential threat to the
ad-funded web simultaneously.

**16.8 Living standards vs. versioned specs.** Living standards track reality and never go
stale; they also mean "conformant" is not a fixed target, which is hard for anyone
building an independent implementation — a point Ladybird and Servo feel directly.

---
