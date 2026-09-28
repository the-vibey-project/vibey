---
id: skill-performance-optimization-1cca419b17
purpose: performance optimization
source: src/vibey_tools/skills/plugins/frontend-design/skills/nextjs-patterns/SKILL.md
requires: ["skill-styling-39ddb79577"]
links: ["skill-security-b1e2d1e835"]
---

## Performance Optimization

### Core Primitives

| Tool            | What it does                                                  | Critical detail                                 |
|-----------------|---------------------------------------------------------------|-------------------------------------------------|
| `next/image`    | Automatic WebP/AVIF, lazy loading, responsive srcset         | Set `priority` on LCP image; always provide `width`/`height` |
| `next/font`     | Self-hosts fonts at build time; zero runtime network request | Eliminates layout shift + external DNS; `display: 'swap'` built-in |
| `next/script`   | Controls third-party script loading strategy                  | `afterInteractive`, `lazyOnload`, experimental `worker` |
| `next/dynamic`  | Code splitting for heavy components                           | `ssr: false` for client-only libs               |
| `@next/bundle-analyzer` | Visualize bundle composition                          | Run with `ANALYZE=true`; set CI size budgets    |

Common bundle culprits: moment.js (→ date-fns/dayjs), full lodash (→ lodash-es or per-method), full icon libraries (→ `optimizePackageImports`).

### PPR / Cache Components

Mental model: *everything outside `<Suspense>` is static, everything inside is dynamic.* The static shell is served from the edge (TTFB ~40–90ms), dynamic holes stream in one HTTP response.

**Best for:** Pages with a stable shell and small dynamic regions (product pages, pricing, marketing surfaces with ~80% cacheable layout, ~20% per-user data).

**Skip PPR for:** 100%-personalized pages (account settings, live dashboards), fully authenticated apps (generic shell has little CDN value).

Debugging: a single `cookies()`/`headers()`/`connection()` call **outside** Suspense makes the route fully dynamic. Use `NEXT_LOG_LEVEL=debug next build` to print why a route is dynamic.

### Turbopack (Default in v16)

- Dev: dramatically faster HMR vs Webpack
- Production: one controlled test (Cal.com) showed ~19% faster median cold build but **~211KB larger shared chunk, +279KB median First Load JS per route** — Turbopack tree-shaking is still maturing
- Measure First Load JS before switching production builds
- Hybrid (Turbopack dev, Webpack prod) is a valid fallback
- Some custom Webpack plugins and Sass custom functions aren't supported

---
