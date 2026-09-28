---
id: skill-mutations-server-actions-70ef777b38
purpose: mutations server actions
source: src/vibey_tools/skills/plugins/frontend-design/skills/nextjs-patterns/SKILL.md
requires: ["skill-data-fetching-patterns-1434db77f6"]
links: ["skill-state-management-581ec0a9f1"]
---

## Mutations: Server Actions

Server Actions compile to **public POST endpoints**. Built-in protections: Origin/Host comparison, POST-only, encrypted non-deterministic action IDs, dead-code elimination.

You **still must:**
1. Validate every input with Zod (`safeParse`, never `parse`)
2. Re-check auth and authorization (IDOR/ownership — don't trust the user's claimed ID)
3. Rate-limit expensive/auth endpoints
4. Avoid leaking secrets through closures (move actions to separate files)

### next-safe-action (recommended)

```tsx
import { createSafeActionClient } from 'next-safe-action'
import { z } from 'zod'

const action = createSafeActionClient()
  .inputSchema(z.object({ id: z.string().cuid() }))
  .action(async ({ parsedInput, ctx }) => {
    // input is already validated; ctx has auth from .use() middleware
    return await updateItem(parsedInput.id)
  })
```

`next-safe-action` provides: composable `.use()` middleware (auth, rate-limit), `useAction`/`useOptimisticAction` hooks, Standard Schema support (Zod, Valibot, ArkType). `zsa` is an alternative.

### Form Hooks (React 19)

- `useActionState` — wraps a Server Action with state (pending, error, data)
- `useFormStatus` — gives `pending` state to submit buttons inside a form
- `useOptimistic` — instant UI feedback while action confirms

---
