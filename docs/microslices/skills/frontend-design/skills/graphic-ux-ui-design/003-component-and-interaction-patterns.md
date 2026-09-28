---
id: skill-component-and-interaction-patterns-8ecf9a6773
purpose: component and interaction patterns
source: src/vibey_tools/skills/plugins/frontend-design/skills/graphic-ux-ui-design/SKILL.md
requires: ["skill-visual-design-fundamentals-d7d4e76546"]
links: ["skill-accessibility-and-inclusive-design-797cb256bc"]
---

## Component and Interaction Patterns

### Navigation

| Pattern    | When to use                                                  |
|------------|--------------------------------------------------------------|
| Top nav    | Marketing sites, shallow IA                                  |
| Side nav   | Deep app-like hierarchies (SaaS, admin)                      |
| Bottom nav | Mobile top-level (3–5 destinations, thumb zone)              |
| Mega menus | Broad e-commerce/content taxonomies                          |

**The "≤7 menu items" rule is a myth** — a misapplication of Miller's Law. Breadth often beats depth; it reduces clicks and keeps users oriented.

### Forms

**Top-aligned labels are the most usable and accessible default.** Advantages over left-aligned:
- Eye travels in one direction (down only)
- Label/field sit close together — ~50ms to move from label to field vs ~500ms for left-aligned (Penzo, 2006 eye-tracking — treat as directional; the accessibility and localization advantages are the more durable case)
- Better on mobile (left-aligned labels truncate the input)

Rules:
- **Never use placeholder text as a label** — it disappears on input, fails contrast, and is unreliable for screen readers
- Floating labels: fashionable but measurably worse for accessibility and motion sensitivity
- Validate inline **after a field is completed**, not on every keystroke
- Keep the submit button enabled; write recovery-oriented error messages
- Break long forms into logical steps

### Buttons and CTAs

Hierarchy: primary → secondary → tertiary/ghost → destructive (visually distinct).

All interactive states must be visually distinct: hover, focus, active, disabled, loading.

**Touch target sizes:**

| Standard     | Minimum          |
|--------------|------------------|
| Apple HIG    | 44×44 pt         |
| Material     | 48×48 dp (~9mm)  |
| WCAG 2.2 AA  | 24×24 CSS px     |
| WCAG 2.5.5 AAA | 44×44 CSS px   |
| visionOS     | 60 pt (gaze-based) |

Aim for the larger platform values.

### Modals and Dialogs

Use for focused, must-complete decisions. Harmful when overused for non-blocking info. Drawers/sheets are better for secondary content and on mobile.

Required for every modal:
- Focus trap
- Restore focus on close
- Support Escape key
- Proper `aria-labelledby`/`aria-describedby`

Inaccessible modals are a top accessibility failure.

### Loading States

| State type       | Best pattern                                      |
|------------------|---------------------------------------------------|
| Content loading  | Skeleton screens (generally reduce perceived wait) |
| Short discrete actions | Spinner                                    |
| No state at all  | Never — worst possible option                     |

Caveat: A 2017 Viget study found skeletons performed *worst* on perceived duration in some conditions. The rule is: show structure for content loading, use a spinner for short discrete actions.

### Lists: Infinite Scroll vs. Pagination vs. Load More

Based on Baymard's multi-year, 50+ site studies:

| Pattern         | Best for                                                  |
|-----------------|-----------------------------------------------------------|
| Load More + lazy-loading | Default; superior for most product lists       |
| Pagination      | Goal-driven look-up, bookmarking, SEO                     |
| Infinite scroll | Exploratory/inspirational feeds (Pinterest, image galleries) |

Infinite scroll "can be downright harmful" for goal-driven search — users lose their place, can't bookmark/compare, the footer becomes unreachable.

### Tables and Data Grids

Provide: sorting, filtering, sticky headers, pagination or "load more." Responsive patterns: horizontal scroll with frozen first column, or card stacking on mobile.

### Notifications

| Type       | Use for                                      | Behavior           |
|------------|----------------------------------------------|--------------------|
| Toast/snackbar | Transient confirmations                  | Auto-dismiss       |
| Banner     | Persistent page-level status                 | Stays until dismissed |
| Inline     | Contextual/field errors                      | Adjacent to source |

Never put critical, action-required info in an auto-dismissing toast.

### Motion and Microinteractions

Dan Saffer's model: trigger → rules → feedback → loops/modes.

Disney timing principles:
- Ease-out for entrances
- Ease-in for exits
- UI transitions: ~150–300ms
- Motion should communicate (state change, spatial relationship, progress), not decorate

**Always honor `prefers-reduced-motion`** — disable or reduce non-essential animation for vestibular safety.

WCAG 2.2 SC 2.5.7: drag interactions must have a single-pointer (non-drag) alternative.

---
