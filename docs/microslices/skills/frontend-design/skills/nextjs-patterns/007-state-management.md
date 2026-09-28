---
id: skill-state-management-581ec0a9f1
purpose: state management
source: src/vibey_tools/skills/plugins/frontend-design/skills/nextjs-patterns/SKILL.md
requires: ["skill-mutations-server-actions-70ef777b38"]
links: ["skill-authentication-bac6dacddc"]
---

## State Management

### Decision Framework

| State type              | Best tool                                      |
|-------------------------|------------------------------------------------|
| URL/shareable (filters, pagination, search) | nuqs (`parseAsInteger`, `parseAsArrayOf`) |
| Server state            | Keep on server; React `cache()` + Server Components |
| Global client UI state  | Zustand (single store) or Jotai (atomic/derived) |
| Form state              | `react-hook-form` + `zodResolver`              |
| Context (theme, locale) | React Context in a Client Component provider  |

**Critical App Router rule:** Never create a global store at module level on the server — it leaks state across requests. Create per-request stores via provider patterns.

### nuqs Caveats

- Not for large/private objects
- Frequent URL updates can cause perf issues — use debouncing/`limitUrlUpdates`
- Does not replace a global client store

### Context Pitfalls

Context providers must be Client Components, don't cross the server/client boundary, and re-render all consumers (performance trap). Use for low-frequency values only.

---
