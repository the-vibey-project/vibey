---
id: skill-9-dashboard-design-87aa5eb11c
purpose: 9 dashboard design
source: src/vibey_tools/skills/plugins/reporting-and-dashboards/skills/reporting-dashboard-design-charts-and-alerting/SKILL.md
requires: []
links: ["skill-10-chart-selection-03668a9586"]
---

## §9. Dashboard Design

> **⚠️ GOTCHA — most dashboards are built and then never opened, and the cause is
> predictable.** **They were built to display available data rather than to support a
> decision.** ⚠️ **The diagnostic question is: "what will someone do differently based on
> this?" If there's no answer, don't build it.**

**⚠️ Know which kind you're building — they have different rules:**
```
OPERATIONAL   ⚠️ monitored continuously; real-time; alerting-adjacent; few metrics,
              large, glanceable
ANALYTICAL    exploratory; filters and drill-down; for analysts
STRATEGIC/EXEC ⚠️ periodic; highly summarized; trend and target-focused; annotated
```
**Structure**: **inverted pyramid — the headline number first, then breakdown, then
detail.** ⚠️ **Above the fold matters; users do not scroll.** **Left-to-right, top-to-bottom
reading order for the primary language.** **Five to nine elements maximum.**

**⚠️ Context is what makes a number actionable, and it's what's usually missing**: **a
number alone is nearly useless.** **Give it a comparison (prior period, target,
benchmark), a trend, and a definition.** ⚠️ **"Revenue: $1.2M" tells you nothing.
"$1.2M, +8% vs last month, 94% of target" tells you what to do.**

**⚠️ Practical rules**: **consistent colour semantics** (⚠️ **pick red-bad/green-good or
brand colours and never mix**), **direct labelling over legends**, **no decoration**
(3D, gradients, unnecessary gridlines), **⚠️ accessible palettes — around 8% of men have
some form of colour vision deficiency, so never encode meaning in red-vs-green alone**,
**mobile consideration if executives read on phones**, and **document every metric
definition where it's displayed, not in a wiki nobody opens.**

---
