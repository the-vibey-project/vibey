---
id: skill-next-js-typescript-frontend-architecture-2a271c4136
purpose: next js typescript frontend architecture
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-architecture/SKILL.md
requires: ["skill-python-backend-architecture-7c85633100"]
links: ["skill-azure-cloud-architecture-6770e0d67a"]
---

## Next.js / TypeScript Frontend Architecture

### Folder Structure: Feature-Sliced Design (FSD)
- Feature-based / FSD is the consensus for large apps
- App Router colocation: route owns `page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx`, plus local `_components`/`_lib`
- FSD layers (shared → entities → features → app) enforce unidirectional dependencies
- Atomic Design is good for the design system but doesn't answer where user scenarios live

### Server / Client Component Boundary (Most Critical Decision)
- Server Components are the **default** — data reads, composition, less JS shipped
- Push `'use client'` **down to interactive leaves** — a `'use client'` at the top of `page.tsx` forfeits most of the benefit
- Shifting to RSCs cuts client JS bundles meaningfully and reduces backend load

### State Management Decision Rules

| State Type | Tool |
|---|---|
| Server data (caching, revalidation, dedup) | **TanStack Query** |
| Forms | **React Hook Form** |
| URL-representable (filters, pagination, tabs) | **URL state** |
| Component-local | **useState** |
| Shared simple | **Zustand** |
| Shared granular / derived values | **Jotai** |
| Complex / strict patterns / time-travel debugging | **Redux Toolkit** |

**Anti-pattern #1 in 2026:** fetching API data into Zustand/Redux and manually syncing it.

### Authentication (2025–2026)
- **CVE-2025-29927** (CVSS 9.1, March 2025): middleware-only auth is bypassable via spoofed `x-middleware-subrequest` header. Always use the **Data Access Layer pattern** — verify auth at every data-access point, not just middleware.
- Cookie hardening: `HttpOnly`, `Secure`, `SameSite`, `__Host-` prefix
- **Clerk**: fastest B2C time-to-production
- **WorkOS**: enterprise SSO
- **Better Auth**: full data ownership in your own DB; took over Auth.js maintenance Sept 2025
- **Auth.js v5**: mainly for existing apps (now in security-patch mode)
- JWT sessions scale without DB lookups but can't be revoked before expiry. Database sessions enable instant "sign out everywhere" but add latency

### Frontend Monorepo: Turborepo
- Structure: `apps/*` + `packages/*` with shared `ui`, `eslint-config`, `typescript-config`, `shared-types`
- Remote caching (content-addressed, shared across devs + CI via Vercel free tier or self-hosted S3-compatible storage with `TURBO_TOKEN`/`TURBO_TEAM`) can cut CI from ~20 minutes to under a minute
- **Don't extract a package until a second consumer appears**

---
