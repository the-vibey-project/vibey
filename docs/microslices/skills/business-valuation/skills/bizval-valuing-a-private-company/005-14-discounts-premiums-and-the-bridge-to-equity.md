---
id: skill-14-discounts-premiums-and-the-bridge-to-equity-7c4d0c979d
purpose: 14 discounts premiums and the bridge to equity
source: src/vibey_tools/skills/plugins/business-valuation/skills/bizval-valuing-a-private-company/SKILL.md
requires: ["skill-13-asset-approach-a1ab6ad862"]
links: ["skill-15-reconcile-report-and-verify-0907075343"]
---

## §14. Discounts, Premiums and the Bridge to Equity

### 14.1 Levels of value and discounts (support each one)
- **Minority/lack of control (MD)**, **lack of marketability (DLOM)**, **key-person**, **customer concentration**, **size/specific-company risk**. Typical DLOM discussions run **~20–35%** in practice (restricted-stock studies, pre-IPO studies, option-pricing models); **courts vary** and state-law "fair value" standards often **disallow** them (§30).
- **Apply sequentially** (multiplicative): `apply_discounts(1000, dlom_pct=25, key_person_pct=10)` → **$675 (−32.5% combined)**.
- **Don't double count:** if the discount rate already includes a company-specific risk premium for concentration, **don't** also discount the value for the same concentration.
- **Control premium** implied by a minority discount `MD`: `1/(1−MD) − 1`; 20% → **25%**.

### 14.2 Premiums
Strategic **synergies**, scarcity, auction dynamics and **investment value** can exceed FMV: legitimate for a buyer's offer, **not** for an FMV appraisal.

### 14.3 EV → equity bridge (cash-free, debt-free deals)
`Equity proceeds = EV − debt − debt-like items − NWC shortfall + cash`.
**Debt-like items:** capital leases, **deferred revenue** (if cash already collected and costs to serve remain), **unpaid taxes**, accrued bonuses/PTO, **customer deposits**, deferred capex, litigation reserves, earnout obligations, shareholder loans. **Example:** EV $5.0M, debt $600k, debt-like $150k, NWC shortfall $100k, cash $250k → **equity $4.4M**.
**Working-capital peg:** set at the **normalized (average) level** over the prior 12 months, adjusted for seasonality; **a peg set too low transfers value to the seller; too high, to the buyer.**

---
