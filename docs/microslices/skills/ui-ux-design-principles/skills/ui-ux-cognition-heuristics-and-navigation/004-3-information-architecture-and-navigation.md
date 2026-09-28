---
id: skill-3-information-architecture-and-navigation-5ceb0725db
purpose: 3 information architecture and navigation
source: src/vibey_tools/skills/plugins/ui-ux-design-principles/skills/ui-ux-cognition-heuristics-and-navigation/SKILL.md
requires: ["skill-2-usability-heuristics-and-mental-models-7c3aeb1de0"]
links: []
---

## §3. Information Architecture and Navigation

### 3.1 The IA questions, in order

1. **What are the objects?** (Not screens — *things*. Documents, orders, patients, tracks.)
2. **What are their attributes and relationships?**
3. **How will people look for them?** (Known-item search vs. exploratory browse vs.
   re-finding something they saw before — these are different behaviours needing
   different affordances.)
4. **What vocabulary do *they* use?** (Not your database's.)
5. **What's the primary organizing scheme?**

**Organizing schemes [DURABLE]:**
- *Exact* schemes (alphabetical, chronological, geographic) — unambiguous, good for
  known-item lookup, useless for exploration.
- *Ambiguous* schemes (by topic, task, audience, metaphor) — support exploration, require
  the user to guess your model. Most product IA is ambiguous, which is why card sorting
  (§12.2 → `ui-ux-writing-forms-research-and-ethics`) exists.
- *Hybrid* schemes fail when they mix at the same level ("Products, Support, For Teams,
  Pricing, 2024 Archive"). Mixing across levels is fine; mixing within one is confusing.

### 3.2 Navigation patterns by form factor

| Pattern | Best for | Capacity | Watch out |
|---|---|---|---|
| **Bottom tab bar** (mobile) | 3–5 top-level, equally important, frequently switched destinations | 5 max (iOS shows "More" beyond 5) | Not for actions. Not for >5. Not for hierarchy. |
| **Navigation drawer / hamburger** | Many destinations, infrequent switching | ~10 | **Measurably reduces discoverability and engagement of hidden items.** Acceptable for secondary nav; bad for primary. |
| **Segmented control / tabs** | Switching *views of the same object* | 2–5 | Not for navigation to different objects |
| **Stack / push navigation** | Drilling into hierarchy | Any depth (but >3 feels lost) | Must show where you are and how to get back |
| **Bottom sheet** | Contextual actions, secondary content, mobile modality | — | Don't nest. Don't hide primary tasks. |
| **Split view / sidebar** (tablet, desktop) | Master–detail | Large | Reflow when narrow; don't just clip |
| **Top nav + mega menu** (web) | Broad, shallow site structure | Large | Keyboard and screen reader support is usually broken |
| **Breadcrumbs** (web, desktop) | Deep hierarchy, orientation | — | Only if a real hierarchy exists; not for linear flows |
| **Command palette** (⌘K) | Expert users, large command surface | Unlimited | Excellent *supplement*, never the only path |
| **Menu bar** (desktop) | Complete, searchable command index | Unlimited | Every command should be here (§8.4 → `ui-ux-design-systems-platforms-and-accessibility`) |

**[CONTESTED] The hamburger menu.** The evidence that hiding navigation reduces usage of
hidden items is strong and replicated. The counterargument is equally real: on a 375 px
screen with eight destinations, there is no alternative that doesn't consume the content
area, and a tab bar with eight items is worse. The defensible position: **use a tab bar for
the 3–5 things people do constantly and a drawer for the long tail**, and never put a
primary revenue or activation path behind the hamburger.

### 3.3 Search

- **If the catalogue is large, search is the primary navigation** — treat it as a feature,
  not a text box in the corner.
- **Support the failure cases**: typos (fuzzy matching), synonyms and the user's vocabulary,
  zero results (offer alternatives, never a dead end), and scoped search (this folder vs.
  everything).
- **Show what was searched and what filters are active.** Losing your query on the results
  page is a top-tier frustration.
- **Autocomplete** shifts the task from recall to recognition — one of the highest-value
  patterns available. Show *categories* of suggestions, not just strings.

### 3.4 Wayfinding — the three questions

Every screen must answer, without effort: **Where am I? Where can I go? How do I get back?**
Mechanisms: persistent nav with a current-state indicator, page titles that match the link
that got you there (label consistency — a startling number of products fail this),
breadcrumbs, and a Back that does what the platform Back is supposed to do.

> **⚠️ GOTCHA — hijacking Back.** On Android, the system Back gesture/button has defined
> semantics. On the web, the browser Back must work in a SPA (History API, not just
> client-side routing that leaves the URL stale). Users trust Back more than they trust
> your UI; breaking it destroys that trust immediately and permanently.
