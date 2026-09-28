---
id: skill-styling-39ddb79577
purpose: styling
source: src/vibey_tools/skills/plugins/frontend-design/skills/nextjs-patterns/SKILL.md
requires: ["skill-testing-patterns-b52d23e80f"]
links: ["skill-performance-optimization-1cca419b17"]
---

## Styling

### Compatibility Matrix

| Approach                    | RSC-compatible | Runtime cost | Notes                              |
|-----------------------------|----------------|--------------|------------------------------------|
| Tailwind CSS                | Yes            | Zero         | Default for new App Router projects; foundation for shadcn/ui |
| CSS Modules                 | Yes            | Zero         | Built-in, scoped, zero-config      |
| vanilla-extract / Panda CSS / StyleX | Yes   | Zero         | Zero-runtime CSS-in-JS             |
| styled-components / Emotion | No (requires `'use client'` boundary and registry) | Runtime | Inherent perf trade-offs in App Router |

**Migration advice:** Don't rip out a working styled-components codebase wholesale. Adopt Tailwind for new components, or move to zero-runtime. Dark mode: `next-themes` with class-based Tailwind `dark:`.

---
