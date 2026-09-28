---
id: skill-next-js-typescript-performance-341b4ed557
purpose: next js typescript performance
source: src/vibey_tools/skills/plugins/frontend-design/skills/performance-optimization/SKILL.md
requires: ["skill-python-performance-059ab084a9"]
links: ["skill-azure-cloud-performance-ad6961f569"]
---

## Next.js / TypeScript Performance

### Core Web Vitals Targets

| Metric | Good threshold | Current web failure rate |
|--------|---------------|--------------------------|
| LCP    | <2.5s         | ~38% of mobile pages fail (HTTP Archive 2025) |
| INP    | <200ms        | ~23% of mobile pages fail; 43% of websites fail per CrUX/Semrush |
| CLS    | <0.1          | ~19% of mobile pages fail |

Only 48% of mobile / 56% of desktop pages pass all three.

**INP replaced FID on March 12, 2024.** INP measures full interaction latency (input delay + processing + presentation) at the 75th percentile across ALL interactions, not just the first.

### What Moves Each Metric

**LCP:**
- Preload the LCP image with `fetchpriority="high"` + `next/image priority`
- Modern formats (AVIF/WebP via `next/image`)
- SSR/static shell so content is in the initial HTML
- Critical CSS inlining

**INP:**
- Break up long JavaScript tasks (>50ms blocks the main thread)
- Defer/facade third-party scripts (YouTube: poster image → iframe on click)
- Self-host analytics
- Passive event listeners; debounce handlers

**CLS:**
- Explicit `width`/`height` on all media (or `aspect-ratio`)
- Reserve space for ads/banners
- `font-display: swap` with matched fallback metrics (`next/font` handles this)

### RSC Bundle Discipline

`"use client"` marks a **module boundary** — everything imported by a client module becomes client-side code. A single misplaced directive silently promotes large subtrees.

**Golden rules:**
1. Push `"use client"` to leaf nodes (only the interactive input, not its parent card)
2. Fetch data in parallel across sibling Server Components
3. Wrap each independent slow dependency in its own `<Suspense>` with a **dimension-matched skeleton** (avoids CLS)
4. Pass Server Components as `children` into Client Component wrappers

Full RSC adoption reports **50–70% First Load JS reduction** and improved INP from reduced hydration cost.

### App Router Caching: The Four Layers

Understanding all four is required to diagnose cache bugs:

| Layer                | Scope              | What it caches                    | Invalidated by          |
|----------------------|--------------------|-----------------------------------|-------------------------|
| Request Memoization  | Single render      | Identical `fetch` calls           | Automatic per render    |
| Data Cache           | Across requests/deploys | `fetch` results with `next: { revalidate, tags }` | `revalidatePath`, `revalidateTag` |
| Full Route Cache     | Across requests    | Prerendered HTML + RSC payload for static routes | Revalidation or rebuild |
| Router Cache         | Client-side in-memory | Visited routes/layouts          | Navigation/time (~30s stale minimum) |

**v15+ change:** `fetch` is no longer cached by default (`no-store`). You opt in with `cache: 'force-cache'` or `next: { revalidate }`.

### PPR / Cache Components

Static shell served from edge (TTFB ~40–90ms) while dynamic holes stream in one HTTP response.

PPR mental model: *everything outside `<Suspense>` is static, everything inside is dynamic.*

**When to use:** Pages with a stable shell and small dynamic regions — product pages, pricing, marketing surfaces where ~80% of layout is cacheable.

**Skip PPR for:** Fully authenticated pages (account settings, live dashboards), high-frequency live data.

**Debugging:** A single `cookies()`/`headers()`/`connection()` call outside Suspense makes the entire route fully dynamic. Use `NEXT_LOG_LEVEL=debug next build` to identify what's forcing dynamic rendering.

Build output marks PPR routes with ◐.

### Turbopack (Default in Next.js 16)

Dev: dramatically faster HMR; claimed ~400% faster `next dev`, 10x HMR on large projects.

Production (Cal.com controlled cold-build test, Next 15.5.2):
- ~19% faster median build (187s → 152s)
- But ~211KB larger shared chunk; +279KB median First Load JS per route (all 151 routes)

**A/B test First Load JS before switching production builds.** Hybrid (Turbopack dev, Webpack prod) is a valid fallback.

### Database from Next.js: Prisma in Serverless

**The connection exhaustion problem:** `connection_limit` is per-instance. 20 pods × pool 20 = 400 connections, potentially exceeding DB max of 300.

**Solutions:**
1. Singleton Prisma client (`globalThis` guard to survive HMR)
2. External pooler: PgBouncer, Prisma Accelerate, or `@prisma/adapter-pg`
3. Set `connection_limit=1` for serverless instances; scale up with the external pooler

**DataLoader pattern for N+1:**
```ts
// Instead of: for each userId, await db.user.findUnique(userId)
// Batch: await db.user.findMany({ where: { id: { in: userIds } } })
```

Real case: per-pod pool reduced to 15 + a concurrency semaphore + DataLoader dropped p95 from 1.8s to 280ms with no schema change.

---
