---
id: skill-11-forms-onboarding-and-conversion-7db671e793
purpose: 11 forms onboarding and conversion
source: src/vibey_tools/skills/plugins/ui-ux-design-principles/skills/ui-ux-writing-forms-research-and-ethics/SKILL.md
requires: ["skill-10-content-and-ux-writing-da276c49a0"]
links: ["skill-12-research-and-evaluation-59954690dd"]
---

## §11. Forms, Onboarding, and Conversion

### 11.1 Form design — where usability turns directly into money

**[DURABLE] Every field you remove increases completion.** Ask only for what you need *now*.

| Rule | Why |
|---|---|
| **One column.** | Multi-column forms cause skipped fields and ambiguous tab order. Exception: genuinely paired short fields (city/state, expiry month/year). |
| **Labels above fields, always visible.** | Fastest to scan; survives zoom; works with autofill; placeholder-as-label is a documented failure. |
| **Group related fields** with clear spacing (§1.3 → `ui-ux-cognition-heuristics-and-navigation`). | Proximity does the work. |
| **Inline validation *after* the field loses focus**, not on every keystroke. | Validating while typing tells users they're wrong before they've finished being right. |
| **Show requirements up front** (password rules, format). | Error prevention > error handling (Nielsen #5). |
| **Correct `autocomplete` attributes and `inputmode`.** | Autofill is a huge completion win and an accessibility feature. `inputmode="numeric"` gives the right mobile keyboard. |
| **Never mask what the user typed** (except passwords, and offer a reveal). | Card numbers, codes, and emails all benefit from being visible for checking. |
| **Mark optional fields, not required ones** — if most are required. | Fewer asterisks, less noise. |
| **Error summary at the top + inline errors + focus the first error.** | Screen-reader users and zoomed users can't see an error 2000 px down. |
| **Preserve entered data on error.** | Losing a filled form is the fastest way to lose a user. |

### 11.2 The checkout/conversion evidence

Baymard Institute's long-running large-scale checkout usability research is the most-cited
data set here. Key figures, with the caveats they deserve:
- **~70.2% average cart abandonment**, from a meta-analysis of ~50 studies (last updated
  Sept 2025). This has been structurally stable for a decade, moving under a percentage
  point in five years.
- Baymard estimates the average large e-commerce site could gain **~35.26% conversion**
  from checkout-design improvements alone — framed by them as an upper bound from a decade
  of documented, solvable issues, **not a guaranteed return**, and explicitly excluding the
  large share of abandonment that is pure browsing intent.
- **Extra costs at checkout** (shipping, fees, tax) are consistently the top abandonment
  reason (~39%); **forced account creation** ~24%; **too long/complicated a checkout**
  ~19%; **not trusting the site with card details** ~19%.
- The average checkout shows **~23.5 form elements / ~14.9 fields**, versus an achievable
  **12–14**; most sites can cut 20–60% of elements.

**⚠️ Cite these carefully.** They are aggregates across many studies and verticals, mostly
from one (excellent, commercial) research organization; live-behaviour trackers report
higher numbers (Dynamic Yield ~77.8% on a rolling 12-month basis) because they measure
something slightly different. Use them to *prioritize*, not as targets your specific site
will hit.

**The practical hierarchy:** show total cost early → offer guest checkout → cut fields →
one obvious next step per screen → visible trust signals near the payment field → support
the payment methods your market actually uses.

### 11.3 Onboarding

- **Show value before you ask for commitment.** Delay signup, delay permissions, delay the
  tour. Permission requests should be *contextual* ("Allow notifications so we can alert
  you when your order ships") and *at the moment of need*, not at first launch — a
  cold-start permission prompt is the most reliable way to get a permanent denial.
- **Progressive onboarding beats a carousel.** Teach the feature when it's first relevant.
  Multi-screen intro carousels are almost universally skipped.
- **Reduce time-to-first-value** relentlessly. Sample data, templates, and sensible defaults
  beat an empty state plus a tutorial.
- **Let users skip, and let them return.** A tour you can't exit is a hostage situation.

---
