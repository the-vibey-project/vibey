---
id: skill-15-anti-patterns-987d3017a6
purpose: 15 anti patterns
source: src/vibey_tools/skills/plugins/ui-ux-design-principles/skills/ui-ux-reference/SKILL.md
requires: []
links: ["skill-16-contested-questions-4559038877"]
---

## §15. Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Placeholder text as the label | Disappears on focus, fails contrast, breaks autofill and translation, invisible to some AT | Persistent label above the field |
| Two primary buttons | Von Restorff: two emphases = none | One primary, rest secondary/tertiary |
| Icon-only controls without labels | Icons aren't universal; tooltips don't exist on touch | Icon + label, or label at minimum |
| Removing focus outlines | WCAG Level A failure; breaks keyboard use | `:focus-visible` with a designed indicator |
| Disabling zoom (`user-scalable=no`) | Hostile to low-vision users; WCAG failure | Never do this |
| Fixed pixel font sizes / ignoring OS text scale | Breaks for everyone over ~45 | Relative units; test at 200% |
| Color as the only signal | Fails ~8% of men and every grayscale/low-vision case | Color + icon + text |
| Confirmation dialogs everywhere | Habituation makes them useless | Undo (§2.3 → `ui-ux-cognition-heuristics-and-navigation`) |
| Hamburger for primary navigation | Measurably reduces discovery of hidden items | Tab bar for the top 3–5 |
| Modal for anything non-blocking | Interrupts, traps, and stacks | Inline, sheet, or side panel |
| Infinite scroll where users need to find and return | Destroys position memory; breaks the footer | Pagination or "load more" |
| Carousels for important content | Very low engagement past slide 1; auto-advance is an a11y failure | Show the content |
| Auto-playing audio/video | Universally hated; a11y violation | User-initiated |
| Hijacking scroll, Back, or system gestures | Breaks the trust users place in platform behaviour | Don't |
| Equal spacing above and below labels | Proximity ambiguity — the classic form bug | Tighter within groups than between |
| Centered long body text | Ragged left edge slows reading | Left-align |
| Full-width text on wide screens | Exceeds 75-character measure | max-width or multi-column |
| Skeleton/spinner with no context | Doesn't reduce anxiety, just delays it | Say what's loading; show progress |
| "Something went wrong" | Unactionable | What/why/what next (§10.2 → `ui-ux-writing-forms-research-and-ethics`) |
| Testing only the happy path | Real pain lives in errors and second sessions | Test failure and recovery |
| Designing only at 1440 px in Figma | Never sees the 375 px reality | Design mobile-first; open the small frame |
| Hiding content on mobile with `display:none` | Mobile users are not second-class | Reorganize, don't delete |
| Optimizing engagement metrics alone | Rewards confusion and manipulation | Pair with quality metrics (§12.4 → `ui-ux-writing-forms-research-and-ethics`) |
| Adding a preference for every disagreement | Pushes design decisions onto users | Choose a good default |
| Accessibility overlay widget | Doesn't work; no legal protection; opposed by AT users | Fix the underlying markup |
| Shipping WCAG 2.0 in 2026 | Below every current legal baseline | Build to 2.2 AA (§9.2 → `ui-ux-design-systems-platforms-and-accessibility`) |
| Quoting "5 users is enough" as universal | Misreads the finding (§12.2 → `ui-ux-writing-forms-research-and-ethics`) | 5 per segment per round, 3 rounds |
| Quoting "7±2" as a menu-length rule | Miller said no such thing (§1.2 → `ui-ux-cognition-heuristics-and-navigation`) | Categorize; don't make people recall |

---
