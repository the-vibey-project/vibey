---
id: skill-data-fetching-patterns-1434db77f6
purpose: data fetching patterns
source: src/vibey_tools/skills/plugins/frontend-design/skills/nextjs-patterns/SKILL.md
requires: ["skill-app-router-rendering-patterns-f9e4cb6371"]
links: ["skill-mutations-server-actions-70ef777b38"]
---

## Data Fetching Patterns

### Caching and Revalidation

In **v15+**, `fetch` is uncached by default. To cache:
- `fetch(url, { cache: 'force-cache' })` — permanent until revalidated
- `fetch(url, { next: { revalidate: 60 } })` — time-based ISR
- `export const revalidate = 60` — segment-level time-based

Invalidation strategies:
- `revalidatePath('/path')` — invalidate all data behind a URL (start here, easier to reason about)
- `revalidateTag('tag')` — fine-grained, invalidates data behind multiple URLs sharing a tag

In **v16 Cache Components** (`use cache`):
- `use cache` directive + `cacheLife()` + `cacheTag()` extends tagging beyond `fetch` to any async work (DB queries, filesystem reads)
- `updateTag()` is Server-Action-only for read-your-own-writes

### Parallelizing Fetches (Avoiding Waterfalls)

```tsx
// BAD: sequential — each waits for the previous
const user = await getUser(id)
const posts = await getPosts(id)

// GOOD: parallel — both fire at once
const [user, posts] = await Promise.all([getUser(id), getPosts(id)])
// Use Promise.allSettled for partial-failure tolerance
```

**Preload pattern** — start a fetch early before a blocking call:
```tsx
void preloadItem(id)  // fire-and-forget, starts fetching immediately
const critical = await getCriticalData()
```

### React cache() for Deduplication

```tsx
import { cache } from 'react'

export const getUser = cache(async (id: string) => {
  return db.user.findUnique({ where: { id } })
})
// Called anywhere in the render tree — executes only once per request
```

Use the `server-only` package to prevent accidental client import of DB-touching functions.

### React Query / SWR with App Router

Still valuable for: client-side caching, optimistic updates, polling/real-time, and direct cache manipulation. Pattern: fetch initial data on the server, hydrate, then use TanStack Query client-side for live updates.

---
