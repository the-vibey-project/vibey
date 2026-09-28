---
id: skill-10-chart-selection-03668a9586
purpose: 10 chart selection
source: src/vibey_tools/skills/plugins/reporting-and-dashboards/skills/reporting-dashboard-design-charts-and-alerting/SKILL.md
requires: ["skill-9-dashboard-design-87aa5eb11c"]
links: ["skill-11-alerting-cb1cafe075"]
---

## §10. Chart Selection

**⚠️ Cleveland and McGill's perceptual ranking is the evidence base and it's worth knowing
in order:**
```
1. Position on a common scale      ⚠️ most accurate — bar and line charts
2. Position on non-aligned scales
3. Length
4. Angle / slope
5. Area                            ⚠️ substantially worse
6. Colour saturation / density     least accurate
```
⚠️ **This is why bar charts beat pie charts for comparison, and it's a measured result
rather than a stylistic opinion.**

| Goal | Chart |
|---|---|
| Compare categories | ⚠️ **Bar (horizontal if labels are long)** |
| Change over time | **Line** (⚠️ many points) or **column** (few) |
| Part-to-whole | **Stacked bar; ⚠️ pie only for 2–3 slices, and reluctantly** |
| Correlation | **Scatter** |
| Distribution | ⚠️ **Histogram, box plot, violin — not a mean** |
| Precise values, many dimensions | ⚠️ **A table. Tables are underrated** |
| Single KPI | **Big number + sparkline + comparison** |
| Geographic | ⚠️ **Choropleth for rates, NOT counts — see below** |

**⚠️ The chart errors that mislead:**
- **Truncated y-axis on a bar chart** — ⚠️ **bars encode length, so truncation
  misrepresents by construction.** **Line charts may be truncated; bars may not.**
- **⚠️ Dual axes** — ⚠️ **you can manufacture any apparent correlation by choosing the
  scales.** **Avoid, or use indexed values on one axis.**
- **⚠️ Choropleth of raw counts** — **you have drawn a population map.** **Normalize.**
- **Pie charts with many slices**; **3D anything**; **rainbow colour scales**
  (⚠️ **perceptually non-uniform — use viridis or similar**).

---
