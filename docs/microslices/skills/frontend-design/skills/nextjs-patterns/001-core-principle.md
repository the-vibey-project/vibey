---
id: skill-core-principle-1af8bb4b9f
purpose: core principle
source: src/vibey_tools/skills/plugins/frontend-design/skills/nextjs-patterns/SKILL.md
requires: []
links: ["skill-version-reality-as-of-june-2026-f687461bba"]
---

## Core Principle

**Default to the server, opt into the client at the leaves.** Keep Server Components as the default; push `'use client'` to the smallest interactive leaf; fetch data on the server (parallelized with `Promise.all`); stream with Suspense; treat every Server Action and Route Handler as a public, unauthenticated endpoint that must independently validate input (Zod) and re-check authorization.
