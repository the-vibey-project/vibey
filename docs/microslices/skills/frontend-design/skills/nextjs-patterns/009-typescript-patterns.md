---
id: skill-typescript-patterns-3bcffc072b
purpose: typescript patterns
source: src/vibey_tools/skills/plugins/frontend-design/skills/nextjs-patterns/SKILL.md
requires: ["skill-authentication-bac6dacddc"]
links: ["skill-testing-patterns-b52d23e80f"]
---

## TypeScript Patterns

### Zod: Runtime Validation Backbone

TypeScript types are erased at runtime. `userId: string` does not stop `{"userId": {"$ne": null}}`.

```tsx
const schema = z.object({ userId: z.string().cuid() })
const result = schema.safeParse(input)
if (!result.success) return { error: result.error.flatten().fieldErrors }
const { userId } = result.data
```

Validate every Server Action and Route Handler input. Infer types with `z.infer<typeof schema>`.

### Typed Routes

Enable `typedRoutes` in `next.config.ts` to catch invalid `<Link href>` at compile time.

### tRPC

Choose tRPC (T3 stack) when you want end-to-end typed RPC across a separate client. tRPC v11 (2025) integrates with RSC — call procedures directly in Server Components. `create-t3-app` scaffolds App Router by default.

---
