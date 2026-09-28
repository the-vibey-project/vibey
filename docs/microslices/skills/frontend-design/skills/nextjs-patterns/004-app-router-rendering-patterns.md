---
id: skill-app-router-rendering-patterns-f9e4cb6371
purpose: app router rendering patterns
source: src/vibey_tools/skills/plugins/frontend-design/skills/nextjs-patterns/SKILL.md
requires: ["skill-architecture-and-project-structure-49107bf3a4"]
links: ["skill-data-fetching-patterns-1434db77f6"]
---

## App Router Rendering Patterns

### Server vs. Client Decision Framework

**Use Server Components (default) for:**
- Data fetching
- Heavy/secret-bearing dependencies (DB, SDKs, API keys)
- Large lists, markdown/MDX
- Composition without interactivity

**Use Client Components (`'use client'`) only for:**
- Interactivity (`onClick`, `useState`, `useEffect`)
- Browser APIs (`window`, `localStorage`, `navigator`)
- Animations, focus management

**Common mistakes:**
- Putting `'use client'` high in the tree — promotes whole subtree, ships unnecessary JS, kills streaming/SEO
- Reading `cookies()`/`headers()` in layouts — forces the whole route dynamic, disables static/PPR
- Fetching with `useEffect` instead of server fetch — delays render, hurts LCP/SEO, creates waterfalls

### Passing Server Components into Client Components

To avoid promoting whole subtrees to the client, pass Server Components as `children`:

```tsx
// DO: server component renders and passes as children prop
<ClientWrapper>{/* server component here */}</ClientWrapper>

// DON'T: importing a server component inside a client component
// (silently promotes it to client)
```

### Layouts, Parallel Routes, and Intercepting Routes

**Layouts:** Cannot pass data to children via props. Each segment that needs data fetches it independently — fetch memoization makes this cheap.

**Parallel routes (`@slot`):** Render multiple independent segments in one layout. Real uses:
- Dashboards with independent streaming/error/loading per pane
- Role-based conditional rendering (the admin slot is never sent to non-admin browsers)
- Every slot needs a `default.tsx` for hard navigations or the app errors

**Intercepting routes (`(.)`, `(..)`, `(...)`):** Combined with parallel routes, the canonical use is modals with shareable URLs — Instagram-style photo overlays, login modals with a standalone `/login` page. Known gotchas:
- `(..)` counts route *segments*, not filesystem levels (`@slot` folders are skipped)
- Multiple parallel slots can show multiple modals
- Modals can persist on parent navigation without a catch-all/conditional

### Loading UI and Error Boundaries

- `loading.tsx` auto-wraps a route in Suspense with the file's content as fallback
- Place Suspense boundaries around distinct data-loading subtrees with **dimension-matched skeleton fallbacks** (avoids CLS)
- Too-coarse boundaries reintroduce waterfalls; too-fine add overhead

**`error.tsx` must be a Client Component:**
```tsx
'use client'
export default function Error({ error, reset }: { error: Error; reset: () => void }) { ... }
```

`global-error.tsx` is the root fallback — must render its own `<html>` and `<body>`, and cannot use providers above it.

---
