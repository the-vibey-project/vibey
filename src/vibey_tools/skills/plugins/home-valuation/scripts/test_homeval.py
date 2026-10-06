#!/usr/bin/env python3
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Worked example + self-test for homeval.py. Synthetic market with KNOWN ground truth so we can
verify the tools recover the right answer. Run: python3 test_homeval.py"""

import math

import homeval as hv
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
TODAY = pd.Timestamp("2026-10-06")

# ---- 1. Synthetic market (ground truth is known) --------------------------------
N = 220
df = pd.DataFrame(
    {
        "sqft": rng.normal(1900, 450, N).clip(900, 3600).round(),
        "beds": rng.choice([2, 3, 3, 4, 4, 5], N),
        "baths": rng.choice([1.5, 2, 2.5, 3], N),
        "lot_sqft": rng.normal(9000, 3000, N).clip(3000, 25000).round(),
        "year_built": rng.integers(1965, 2022, N),
        "condition": rng.integers(2, 6, N),
        "garage": rng.choice([0, 1, 2, 2, 3], N),
        "has_pool": rng.random(N) < 0.08,
        "style": rng.choice(["ranch", "two-story"], N),
    }
)
df["lat"] = 34.9 + rng.normal(0, 0.006, N)
df["lon"] = -82.4 + rng.normal(0, 0.006, N)
df["sale_date"] = TODAY - pd.to_timedelta(rng.integers(5, 330, N), unit="D")
months_ago = (TODAY - df.sale_date).dt.days / 30.44
MONTHLY_DRIFT = 0.15 / 100  # truth: +0.15%/month
TRUE_ELAST_SQFT = 0.85


# Module-level by design (ADR-0016): the toolkit's self-test, run as a plain script.
def true_price(r, mago):
    base = 250_000 * (r.sqft / 1900) ** TRUE_ELAST_SQFT
    base *= (r.lot_sqft / 9000) ** 0.06
    base *= math.exp(0.012 * (r.baths - 2) * 2)
    base *= math.exp(-0.0022 * (2026 - r.year_built))
    base *= math.exp(0.035 * (r.condition - 3))
    base *= math.exp(0.018 * (r.garage - 2))
    base *= (1 + MONTHLY_DRIFT) ** (-mago)  # older sales were cheaper
    return base


df["true_price"] = [true_price(r, m) for (_, r), m in zip(df.iterrows(), months_ago, strict=True)]
df["sale_price"] = (df.true_price * np.exp(rng.normal(0, 0.045, N))).round(-2)
df["list_price"] = (df.sale_price * np.exp(rng.normal(0.01, 0.02, N))).round(-2)
cut = rng.random(N) < 0.35
df["orig_list_price"] = (
    df.list_price * np.where(cut, np.exp(np.abs(rng.normal(0.03, 0.015, N))), 1.0)
).round(-2)
df["dom"] = rng.integers(5, 90, N)

# ---- 2. Subject -------------------------------------------------------------------
subj = hv.Subject(
    sqft=2000,
    beds=4,
    baths=2.5,
    lot_sqft=9500,
    year_built=2004,
    condition=4,
    garage=2,
    has_pool=False,
    lat=34.9,
    lon=-82.4,
    style="two-story",
)
subj_truth = true_price(
    pd.Series(dict(sqft=2000, lot_sqft=9500, baths=2.5, year_built=2004, condition=4, garage=2)), 0
)
print(f"GROUND TRUTH value today: ${subj_truth:,.0f}\n")

# ---- 3. Market stats ----------------------------------------------------------------
recent = df[(TODAY - df.sale_date).dt.days <= 90]
print(
    "market_stats (last 90d):",
    {k: round(v, 2) if isinstance(v, float) else v for k, v in hv.market_stats(recent).items()},
)
print(
    "months_of_supply(180 active, 540 closed/12m) =",
    round(hv.months_of_supply(180, 540), 2),
    "->",
    hv.classify_market(hv.months_of_supply(180, 540)),
)

# ---- 4. Market drift estimate ------------------------------------------------------------
drift = hv.time_adjustment_pct_per_month(df)
print(f"\nestimated drift: {drift:.3f}%/mo (truth +0.15%/mo; noisy by design)")

# ---- 5. Comps: score, select, adjust, reconcile ---------------------------------------------
ranked = hv.score_comps(subj, df, TODAY)
good = ranked[ranked.within_guardrails].head(6)
print(f"\ncomps within guardrails: {int(ranked.within_guardrails.sum())}; using top {len(good)}")
adj = hv.adjust_comps(
    subj,
    good,
    TODAY,
    monthly_drift_pct=max(min(drift, 0.5), -0.5),
    bath_adj=7500,
    garage_bay_adj=8000,
    lot_per_sqft=0.0,
)
pd.set_option("display.width", 200)
print(
    adj[
        [
            "sale_price",
            "time",
            "gla",
            "baths",
            "garage",
            "condition",
            "net_adj",
            "adjusted_price",
            "net_pct",
            "gross_pct",
            "flag",
        ]
    ]
    .round(0)
    .to_string()
)
rec = hv.reconcile(adj, scores=good.score)
print("\nreconcile:", {k: (round(v) if isinstance(v, float) else v) for k, v in rec.items()})
err_comps = 100 * (rec["estimate"] - subj_truth) / subj_truth
print(f"comps-approach error vs truth: {err_comps:+.2f}%")

# ---- 6. Hedonic regression cross-check -----------------------------------------------------------
m = hv.hedonic_fit(df, TODAY)
pred = hv.hedonic_predict(m, subj)
print(f"\nhedonic: n={m['n']} R2={m['r2']:.3f}  resid sd (log) = {m['resid_sd_log']:.3f}")
print(
    f"  elasticity on sqft = {m['beta']['ln_sqft']:.3f} (truth {TRUE_ELAST_SQFT}), monthly drift coef = {100 * m['beta']['months']:.3f}%/mo (truth 0.15)"
)
print(
    f"  point ${pred['point']:,.0f}  p10-p90 ${pred['p10']:,.0f}-${pred['p90']:,.0f}  implied MdAPE ~{pred['approx_mdape_pct']:.1f}%"
)
print(f"  error vs truth: {100 * (pred['point'] - subj_truth) / subj_truth:+.2f}%")

# ---- 7. Triangulate ----------------------------------------------------------------------------------
tri = 0.6 * rec["estimate"] + 0.4 * pred["point"]
print(
    f"\ntriangulated (60% comps / 40% regression): ${tri:,.0f}  error vs truth {100 * (tri - subj_truth) / subj_truth:+.2f}%"
)
print(
    "off-market AVM-style band at 7.2% median error:", tuple(round(x) for x in hv.price_band(tri))
)

# ---- 8. Assertions (the self-test) -----------------------------------------------------------------------
assert abs(err_comps) < 6, "comps approach should land within ~6% of truth in this synthetic market"
assert abs(100 * (pred["point"] - subj_truth) / subj_truth) < 6, "regression within ~6%"
assert 0.6 < m["beta"]["ln_sqft"] < 1.1, "sqft elasticity should be recovered near 0.85"
assert (
    hv.classify_market(3.0) == "seller's market"
    and hv.classify_market(5.0) == "balanced"
    and hv.classify_market(7) == "buyer's market"
)

# ---- 9. Buyer math ----------------------------------------------------------------------------------------
print("\n--- BUYER ---")
p = hv.piti(
    price=429_100,
    down_pct=10,
    rate_pct=7.28,
    tax_rate_pct=0.9,
    insurance_annual=3057,
    hoa_monthly=0,
    pmi_rate_pct=0.6,
)
print({k: round(v) for k, v in p.items()})
base = hv.piti(429_100, 10, 6.01, 0.9, 3057, 0, 0.6)["total"]
print(
    f"same house at Feb-2026 low (6.01%): ${base:,.0f}/mo vs ${p['total']:,.0f}/mo at 7.28%  (+${p['total'] - base:,.0f}/mo)"
)
tc = hv.true_monthly_cost(p["total"], 429_100, 1.0, 250)
print("true monthly cost:", {k: round(v) for k, v in tc.items()})
ceiling = hv.max_price_from_payment(2600, 10, 7.28, 0.9, 3057, 0, 0.6)
print(f"max price for $2,600/mo all-in at 7.28%, 10% down: ${ceiling:,.0f}")
assert abs(hv.piti(ceiling, 10, 7.28, 0.9, 3057, 0, 0.6)["total"] - 2600) < 1
print("dti:", {k: round(v, 1) for k, v in hv.dti(p["total"], 600, 9000).items()})
print(
    "appraisal gap:",
    hv.appraisal_gap_plan(
        offer=430_000, appraised=418_000, down_payment=43_000, cash_reserve=15_000
    ),
)

# ---- 10. Seller math ------------------------------------------------------------------------------------------
print("\n--- SELLER ---")
sn = hv.seller_net(
    price=429_100,
    mortgage_payoff=210_000,
    listing_comm_pct=2.5,
    buyer_comm_pct=2.5,
    seller_concessions_pct=1.5,
    transfer_tax_pct=0.2,
    title_escrow_pct=0.5,
    prep_costs=4_500,
    repairs_credit=2_000,
    prorated_taxes_hoa=1_200,
)
print({k: round(v, 1) for k, v in sn.items()})
print(
    "cost of waiting 3 months (carry $2,900/mo+$300, drift 0.0%/mo):",
    {k: round(v) for k, v in hv.carrying_cost_of_waiting(2900, 300, 3, 429_100, 0.0).items()},
)
print(
    "home sale gain:",
    {
        k: round(v)
        for k, v in hv.home_sale_gain(429_100, 25_000, 300_000, 6_000, 20_000, "single").items()
    },
)

# ---- 11. Investment ---------------------------------------------------------------------------------------------------
print("\n--- INVESTMENT ---")
n = hv.noi(gross_scheduled_rent=2_400 * 12, vacancy_pct=6, opex=9_800)
print(
    f"NOI ${n:,.0f}; cap at $360k = {hv.cap_rate(n, 360_000):.2f}%; value at 6.5% cap = ${hv.value_from_cap(n, 6.5):,.0f}"
)
print(f"GRM = {hv.grm(360_000, 2_400 * 12):.1f}")
ds = hv.monthly_pi(360_000 * 0.75, 7.28) * 12
print(
    f"debt service ${ds:,.0f}; DSCR = {hv.dscr(n, ds):.2f}; CoC = {hv.cash_on_cash(n, ds, 360_000 * 0.25 + 10_800):.2f}%"
)
print(
    "BRRRR:",
    {
        k: round(v, 2)
        for k, v in hv.brrrr(210_000, 55_000, 330_000, 75, 2_300, 40, 7.28, 8_000).items()
    },
)
print(
    "70% rule max offer on $330k ARV, $55k rehab:",
    hv.seventy_percent_rule_max_offer(330_000, 55_000),
)
rb = hv.rent_vs_buy(429_100, 10, 7.28, 0.9, 3057, 1.0, 2_400, 7, 2.5, 3.0, 6.0)
print("rent vs buy 7y:", {k: (round(v) if isinstance(v, float) else v) for k, v in rb.items()})
print(
    "rent vs buy 7y @ 5% appreciation:",
    hv.rent_vs_buy(429_100, 10, 7.28, 0.9, 3057, 1.0, 2_400, 7, 5.0, 3.0, 6.0)["winner"],
)
print(
    "rent vs buy 7y @ 0% appreciation:",
    hv.rent_vs_buy(429_100, 10, 7.28, 0.9, 3057, 1.0, 2_400, 7, 0.0, 3.0, 6.0)["winner"],
)

print("\nALL ASSERTIONS PASSED")
