---
id: skill-7-design-systems-and-tokens-87b471c0fb
purpose: 7 design systems and tokens
source: src/vibey_tools/skills/plugins/ui-ux-design-principles/skills/ui-ux-design-systems-platforms-and-accessibility/SKILL.md
requires: []
links: ["skill-8-platform-conventions-99ec8151b2"]
---

## §7. Design Systems and Tokens

### 7.1 What a design system actually is

Not a component library. A design system is **a set of shared decisions, encoded so they
can't drift** — plus the governance that keeps them shared. It has four layers:

```
Principles        — how we decide (rarely written well, hugely valuable when it is)
Foundations       — tokens: color, type, space, radius, elevation, motion, breakpoints
Components        — buttons, inputs, dialogs; with documented props, states, a11y behaviour
Patterns          — how components compose into recurring solutions (forms, empty states,
                    destructive flows, onboarding, data tables)
```
Plus: documentation, contribution model, versioning, deprecation policy, and adoption
metrics. **A component library without governance decays into a component graveyard.**

### 7.2 Token architecture — the three-tier model

```
Tier 1  PRIMITIVE / global    blue-500 = #3B82F6      spacing-4 = 16px
          ↓ referenced by
Tier 2  SEMANTIC / alias      color.action.primary → blue-500       (light)
                              color.action.primary → blue-300       (dark)
                              space.stack.md → spacing-4
          ↓ referenced by
Tier 3  COMPONENT-SPECIFIC    button.primary.background → color.action.primary
```
**[DURABLE] Components must only ever reference tiers 2 and 3.** The moment a component
hardcodes `blue-500`, you cannot theme, cannot do dark mode without a rewrite, and cannot
rebrand. This one rule is most of the value of tokens.

**The DTCG spec is now real.** The **W3C Design Tokens Community Group published its first
stable specification, version 2025.10, on 28 October 2025** — a vendor-neutral JSON
interchange format with `$value`/`$type`, composite types (shadows, gradients, typography
sets, transitions, borders), references that survive transforms, groups, `$description`,
`$extensions`, `$deprecated`, multi-file support, and modern color spaces. It was developed
with 20+ editors from Adobe, Google, Microsoft, Meta, Salesforce, Figma, Shopify, Sketch,
Penpot and others.

**⚠️ Precision matters here:** it is a **W3C *Community Group* specification, not a W3C
Recommendation** — stable and production-ready, but not on the Standards Track. Say
"the DTCG specification" rather than "the W3C standard" when accuracy counts.

Tooling as of 2026: **Style Dictionary v4** ships first-class DTCG support (full 2025.10
support is landing in v5); Figma Variables can export to the format; Tokens Studio,
Terrazzo, Penpot, Supernova, Knapsack and zeroheight support or are implementing it. File
convention: `.tokens` / `.tokens.json`, media type `application/design-tokens+json`.

```json
{
  "color": {
    "$type": "color",
    "blue": { "500": { "$value": "#3b82f6" }, "300": { "$value": "#93c5fd" } },
    "action": {
      "primary": {
        "$value": "{color.blue.500}",
        "$description": "Primary interactive fill. Light theme."
      }
    }
  },
  "space": {
    "$type": "dimension",
    "4": { "$value": { "value": 16, "unit": "px" } }
  }
}
```

**A token pipeline that works:**
```
Figma Variables / Tokens Studio
   → push branch → GitHub PR
      → CI: JSON-schema validate against DTCG
              lint (no orphan tokens, no missing $type, no raw hex in components,
                    contrast check on every semantic fg/bg pair)
              build via Style Dictionary → CSS custom properties, Swift, Kotlin, JSON
              visual regression on the component library
      → merge → versioned release → consumed by apps
```
**[DURABLE] The hard part was never the format.** It's governance: who can add a token, how
deprecation works, how you stop 400 one-off values from accumulating, and how you get teams
to actually adopt. The DTCG spec closed the interoperability problem; it did not close the
organizational one.

### 7.3 Component API design

Treat components as an API with a compatibility contract:
- **Props over variants-by-copy.** One Button with `variant`, `size`, `state` — not five
  Buttons.
- **Composition over configuration** for anything open-ended. A `Card` that accepts
  children beats a `Card` with 22 boolean props.
- **Accessibility is inside the component, not a documentation note.** If the Dialog
  component doesn't trap focus, restore focus, and wire `aria-modal`, every consumer will
  get it wrong.
- **Every component documents: purpose, when *not* to use it, all states, keyboard
  behaviour, a11y notes, and do/don't examples.** The "when not to use" section is the one
  people skip and the one that prevents misuse.
- Version with semver; deprecate with a documented migration and a codemod where possible.

### 7.4 Measuring adoption

A design system's only real metric is **adoption**: percentage of UI built from system
components, number of one-off/detached components, token coverage vs. hardcoded values,
time-to-ship a standard screen. Design-token adoption is now the norm rather than the
exception (an industry survey of ~300 professionals reported ~84% team adoption in 2026,
up from ~56% a year earlier) — so the differentiating question has moved from "do you use
tokens" to "is the token graph actually the single source of truth."

---
