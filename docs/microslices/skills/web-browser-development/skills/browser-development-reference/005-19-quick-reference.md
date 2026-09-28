---
id: skill-19-quick-reference-184e7caa88
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/web-browser-development/skills/browser-development-reference/SKILL.md
requires: ["skill-18-the-canon-8ee59aa692"]
links: ["skill-20-sources-and-method-451c88ada2"]
---

## §19. Quick Reference

### 19.1 Numbers
- Frame budget: **16.6 ms @ 60 Hz**, **8.3 ms @ 120 Hz** — for *everything*.
- Engine share: Blink **~81%**, WebKit **~14%**, Gecko **~3%**.
- Interop 2025 overall score: **25 → 95**; Firefox **46 → 99**.
- Baseline *Widely available* = *Newly available* **+ 30 months**.
- Memory-safety bugs ≈ **70%** of serious browser vulnerabilities historically.
- MiracleObject target: neutralize up to **90%** of GPU-main-thread UAFs.
- ~**17–20%** of global traffic blocks third-party cookies by default regardless of Chrome.

### 19.2 "Why is this page slow?" — triage order
1. **Network**: TTFB, blocking subresources, no preload, no compression, uncached.
2. **Main thread**: long tasks, parse/compile cost, forced synchronous layout (§7.3 → `browser-rendering-pipeline`).
3. **Style**: huge selector count, invalidation storms from class toggles on ancestors.
4. **Layout**: layout thrashing, deep flex/grid nesting, table layout.
5. **Paint/raster**: large paint areas, no layer promotion, or too many layers.
6. **Compositing**: main-thread scroll (non-passive listeners), non-composited animations.
7. **GPU/memory**: texture memory exhaustion, checkerboarding.

### 19.3 Browser security review checklist
- [ ] Does this feature let a renderer assert something the browser process trusts?
- [ ] Is every IPC field validated in the privileged process?
- [ ] Does it read cross-origin data into a renderer that shouldn't have it? (CORB/ORB)
- [ ] Does it add a timing signal usable for Spectre?
- [ ] Does it add fingerprinting entropy, and has that been quantified?
- [ ] Is it restricted to secure contexts? Permissions-Policy delegable?
- [ ] Is storage partitioned by top-level site?
- [ ] What is the permission UX, and can it be spoofed by page content?
- [ ] Does it parse untrusted binary input, and in what language, in which process?
- [ ] Is there an origin trial, a use counter, and a removal path?

---
