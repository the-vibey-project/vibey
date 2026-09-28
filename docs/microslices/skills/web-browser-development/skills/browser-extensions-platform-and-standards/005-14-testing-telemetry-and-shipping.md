---
id: skill-14-testing-telemetry-and-shipping-9a178cbf61
purpose: 14 testing telemetry and shipping
source: src/vibey_tools/skills/plugins/web-browser-development/skills/browser-extensions-platform-and-standards/SKILL.md
requires: ["skill-13-standards-and-interop-0cb5fe5d58"]
links: []
---

## §14. Testing, Telemetry, and Shipping

**Testing layers**: unit tests; **WPT** for conformance; **reference tests** (render two
documents that should look identical — the standard technique for layout and paint, since
pixel-exact expectations are unmaintainable across platforms); pixel tests with tolerance;
performance benchmarks (Speedometer, JetStream, MotionMark) *plus* real-page corpora;
**fuzzing** (Domato-style DOM fuzzers, IPC fuzzers, format fuzzers — a browser is one of
the most-fuzzed artifacts in existence); and cluster-scale **crawler-based regression
testing** against millions of real sites, because real sites are the actual spec.

**Shipping a web feature** — the process every engine now follows in some form: an
explainer, a spec, cross-vendor **standards positions**, security and privacy review,
WPT coverage, an **origin trial** (time-limited real-world testing on real sites), a
**use-counter** measuring how much of the web touches it, then enable by default —
and the knowledge that **you can essentially never remove it afterwards** without a
deprecation trial and a use-counter approaching zero.

**Release cadence**: Chrome and Firefox ship roughly every 4 weeks with channels
(canary/nightly → dev/beta → stable) and staged percentage rollouts with kill switches.
**A browser is an always-on auto-update channel into hundreds of millions of machines** —
that pipeline is itself critical security infrastructure.
