---
id: skill-architecture-and-project-structure-49107bf3a4
purpose: architecture and project structure
source: src/vibey_tools/skills/plugins/frontend-design/skills/nextjs-patterns/SKILL.md
requires: ["skill-version-reality-as-of-june-2026-f687461bba"]
links: ["skill-app-router-rendering-patterns-f9e4cb6371"]
---

## Architecture and Project Structure

### Key Rule: `app/` is for Routing Only

Keep `page.tsx`/`layout.tsx` thin. Move logic into a feature/domain structure:

```
src/
  app/              # routing only — thin page/layout files
  features/         # domain logic: auth/, products/, checkout/
  server/           # DAL, DB queries, service functions
  lib/              # shared pure utilities
  components/       # genuinely shared UI
```

**Why not layer-based buckets (`components/`, `hooks/`, `utils/`)?** They read well early but degrade into high-fan-in dependency magnets at scale. Feature-based structure keeps a feature's code together and makes it testable and deletable.

### Colocation

Folders in `app/` are not routable until a `page`/`route` file exists. Safely colocate components, tests, and utilities inside route segments.

- `_folderName` — private folder excluded from routing
- `(groupName)` — route group: organizes without affecting URL; enables multiple root layouts

### Data Access Layer (DAL)

Establish a DAL from day one — a service/repository layer that:
- Is the only place that touches the database
- Re-verifies auth/authorization before every read or mutation
- Is independently testable (pure functions, no Next.js coupling)
- Is reusable across Server Actions, Route Handlers, webhooks, and cron jobs

Putting business logic directly in Server Actions makes it untestable; extract pure service functions.

### Monorepo (Turborepo)

Turborepo is the default (maintained by Vercel). Critical configuration:
- Set `outputs` in `turbo.json` or every task rebuilds from scratch
- Build shared packages before dependent apps
- Use `transpilePackages` for internal packages
- Use `output: 'standalone'` + correct `outputFileTracingRoot` for deploying a single app

**Barrel exports:** Large `index.ts` barrels hurt dev compile time and tree-shaking. `experimental.optimizePackageImports` auto-rewrites named imports for known libraries (lucide-react, @mui/material) — but does NOT reliably work for internal workspace packages with Turbopack/symlinks (pnpm). For your own barrel files, refactor to direct imports.

---
