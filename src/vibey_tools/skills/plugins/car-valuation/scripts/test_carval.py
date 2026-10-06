#!/usr/bin/env python3
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Worked example + self-test for carval.py using a SYNTHETIC market with a known true price function.
Run: python3 test_carval.py"""

import math

import carval as cv
import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
TODAY = pd.Timestamp("2026-10-06")
MSRP = {"LX": 28_000, "EX": 31_500, "Touring": 36_000}
DRIFT = -0.004  # truth: -0.4%/month wholesale-driven drift (autumn softening)


# Module-level by design (ADR-0016): the toolkit's self-test, run as a plain script.
def true_price(year, miles, trim, cond, acc, owners, months_ago, cpo=False):
    age = TODAY.year - year
    base = MSRP[trim] * cv.retention_curve(age)  # model-year depreciation
    exp_miles = 12_000 * max(age, 0.5)
    base *= math.exp(-0.022 * (miles - exp_miles) / 10_000)  # ~2.2% per 10k miles vs expectation
    base *= math.exp(0.030 * (cond - 3))  # condition
    base *= (1 - 0.07) ** acc  # accident history
    base *= (1 - 0.01) ** (owners - 1)
    base *= (1 + DRIFT) ** (-months_ago)
    return base + (1_500 if cpo else 0)


# ---- synthetic market: 260 listings/sales of ONE model (3 trims, 2019-2024) ---------------------------------
N = 260
df = pd.DataFrame(
    {
        "year": rng.integers(2019, 2025, N),
        "trim": rng.choice(list(MSRP), N, p=[0.35, 0.4, 0.25]),
        "condition": rng.choice([2, 3, 3, 4, 4, 5], N),
        "accidents": rng.choice([0, 0, 0, 0, 1, 2], N),
        "owners": rng.choice([1, 1, 2, 3], N),
        "cpo": rng.random(N) < 0.12,
        "status": rng.choice(["sold", "active"], N, p=[0.55, 0.45]),
        "region_ok": rng.random(N) < 0.93,
    }
)
df["miles"] = (
    (12_000 * (TODAY.year - df.year).clip(lower=0.5) * rng.normal(1.0, 0.25, N))
    .clip(2_000, 160_000)
    .round(-2)
)
df["list_date"] = TODAY - pd.to_timedelta(rng.integers(3, 150, N), unit="D")
mago = (TODAY - df.list_date).dt.days / 30.44
df["true"] = [
    true_price(r.year, r.miles, r.trim, r.condition, r.accidents, r.owners, m, r.cpo)
    for r, m in zip(df.itertuples(), mago, strict=True)
]
noise = np.exp(rng.normal(0, 0.03, N))
# sold = transaction price; active = asking price ~ +3% above transaction on average
df["price"] = np.where(df.status == "sold", df.true * noise, df.true * noise * 1.03).round(-1)

# ---- subject ----------------------------------------------------------------------------------------------
subj = cv.Vehicle(year=2022, miles=38_000, trim="EX", condition=4, owners=1, accidents=0, cpo=False)
truth = true_price(2022, 38_000, "EX", 4, 0, 1, 0)
print(f"GROUND TRUTH transaction value today: ${truth:,.0f}\n")

# ---- 1. comps -----------------------------------------------------------------------------------------------
ranked = cv.score_listings(subj, df, TODAY)
good = ranked[ranked.within_guardrails]
print(
    f"comps within guardrails: {len(good)} (sold {int((good.status == 'sold').sum())}, active {int((good.status == 'active').sum())})"
)
band = df[(df.trim == "EX") & (df.year.between(2021, 2023))]
per_mile = abs(cv.mileage_adjustment_per_mile(band))
print(
    f"estimated mileage adjustment: ${per_mile:.3f}/mile (truth ~ 0.022 x ~$22k / 10k = ~$0.05/mi)"
)
top = good.head(6)
adj = cv.adjust_listings(
    subj,
    top,
    TODAY,
    per_mile=per_mile,
    ask_to_sale_discount_pct=3.0,
    condition_step_pct=3.0,
    accident_pct=7.0,
    owner_step_pct=1.0,
    monthly_drift_pct=-0.4,
    year_step_pct=7.0,
)
pd.set_option("display.width", 220)
print(
    adj[
        [
            "price",
            "ask_to_sale",
            "time",
            "miles",
            "year",
            "condition",
            "accident",
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
rec = cv.reconcile(adj)
err_c = 100 * (rec["estimate"] - truth) / truth
print(
    f"\nreconcile: ${rec['estimate']:,.0f}  range {tuple(round(x) for x in rec['range_best'])}  spread {rec['spread_pct']:.1f}%  -> error {err_c:+.2f}%"
)

# ---- 2. regression -----------------------------------------------------------------------------------------------
# treat asking as +3% (deflate actives first) so the regression is on transaction-equivalent prices
d2 = df.copy()
d2["price"] = np.where(d2.status == "active", d2.price / 1.03, d2.price)
m = cv.hedonic_fit(d2, TODAY)
pred = cv.hedonic_predict(m, subj, TODAY)
print(
    f"\nhedonic: n={m['n']} R2={m['r2']:.3f} resid sd={m['resid_sd_log']:.3f}  age coef={m['beta']['age']:.3f}/yr  per10k miles={m['beta']['per10k_miles']:.3f}  months={100 * m['beta']['months']:.2f}%/mo"
)
print(
    f"  point ${pred['point']:,.0f}  p10-p90 ${pred['p10']:,.0f}-${pred['p90']:,.0f}  MdAPE~{pred['approx_mdape_pct']:.1f}%  error {100 * (pred['point'] - truth) / truth:+.2f}%"
)
tri = 0.6 * rec["estimate"] + 0.4 * pred["point"]
print(f"triangulated 60/40: ${tri:,.0f}  error {100 * (tri - truth) / truth:+.2f}%")
assert abs(err_c) < 6 and abs(100 * (pred["point"] - truth) / truth) < 6, (
    "valuation methods should land within ~6% in the synthetic market"
)
assert abs(100 * (tri - truth) / truth) < 5

# ---- 3. naive method for contrast: raw average asking price of the same model ----------------------------------------
naive = df[(df.trim == "EX") & (df.year.between(2021, 2023))].price.mean()
print(
    f"\nNAIVE mean asking/sold of same trim, 2021-23: ${naive:,.0f}  error {100 * (naive - truth) / truth:+.1f}%  (why mileage/condition/status adjustments matter)"
)


# ---- 3b. Monte-Carlo accuracy: 120 random subjects, 3 methods vs ground truth ---------------------------------------------------
errs = {"naive same-trim mean": [], "adjusted comps": [], "hedonic": [], "triangulated": []}
for _ in range(120):
    sv = cv.Vehicle(
        year=int(rng.integers(2020, 2024)),
        miles=float(rng.integers(15, 80) * 1_000),
        trim=str(rng.choice(list(MSRP))),
        condition=int(rng.integers(2, 6)),
        owners=int(rng.integers(1, 3)),
        accidents=int(rng.choice([0, 0, 1])),
    )
    tv = true_price(sv.year, sv.miles, sv.trim, sv.condition, sv.accidents, sv.owners, 0)
    nv = df[(df.trim == sv.trim) & (df.year.between(sv.year - 1, sv.year + 1))].price.mean()
    rk = cv.score_listings(sv, df, TODAY)
    tp = rk[rk.within_guardrails].head(6) if rk.within_guardrails.sum() >= 3 else rk.head(6)
    pm = (
        abs(
            cv.mileage_adjustment_per_mile(
                df[(df.trim == sv.trim) & df.year.between(sv.year - 1, sv.year + 1)]
            )
        )
        or 0.04
    )
    ad = cv.adjust_listings(
        sv,
        tp,
        TODAY,
        per_mile=pm,
        ask_to_sale_discount_pct=3.0,
        accident_pct=7.0,
        monthly_drift_pct=-0.4,
    )
    ec = cv.reconcile(ad)["estimate"]
    eh = cv.hedonic_predict(m, sv, TODAY)["point"]
    for k, v in [
        ("naive same-trim mean", nv),
        ("adjusted comps", ec),
        ("hedonic", eh),
        ("triangulated", 0.6 * ec + 0.4 * eh),
    ]:
        errs[k].append(abs(v - tv) / tv * 100)
print("\nMdAPE over 120 random subjects (synthetic truth):")
for k, v in errs.items():
    print(f"  {k:22s} median abs err {np.median(v):5.1f}%   90th pct {np.percentile(v, 90):5.1f}%")
assert np.median(errs["hedonic"]) < np.median(errs["naive same-trim mean"])

# ---- 4. channels ----------------------------------------------------------------------------------------------------------
print("\n--- SELLING CHANNELS (placeholder spreads) ---")
retail = tri * 1.06  # dealer retail ~ above private-party
ch = cv.channel_values(retail)
print({k: round(v) for k, v in ch.items()})
credit = cv.tradein_tax_credit_value(ch["dealer_tradein"], 6.0, True)
nets = [
    cv.sell_net("trade-in (state credit)", ch["dealer_tradein"], payoff=15_000, tax_credit=credit),
    cv.sell_net("instant offer", ch["instant_offer"], payoff=15_000),
    cv.sell_net(
        "private party",
        ch["private_party"],
        payoff=15_000,
        listing_cost=150,
        prep_cost=250,
        hours=8,
        hourly_value=25,
        risk_haircut_pct=1.0,
    ),
]
for n in nets:
    print({k: (round(v) if isinstance(v, float) else v) for k, v in n.items()})

# ---- 5. buyer math ----------------------------------------------------------------------------------------------------------
print("\n--- LOANS / OTD / NEGATIVE EQUITY ---")
price = 31_500
print("payment $43,610 @6.35% x 69.5 mo ~", round(cv.loan_payment(43_610, 6.35, 70)))
print(
    cv.term_comparison(price, {48: 6.5, 60: 6.9, 72: 7.5, 84: 8.5}).round(1).to_string(index=False)
)
o = cv.otd_price(
    price,
    doc_fee=500,
    addons=1_200,
    sales_tax_rate_pct=6.0,
    title_reg=350,
    trade_value=9_000,
    state_trade_credit=True,
)
print({k: round(v) for k, v in o.items()})


# Module-level by design (ADR-0016): the toolkit's self-test, run as a plain script.
def value_fn(mth: float) -> float:
    return price * cv.retention_curve(mth / 12.0) * 0.97  # model-year depreciation placeholder


for term, apr in [(48, 6.5), (72, 7.5), (84, 8.5)]:
    ne = cv.negative_equity_months(
        price + 1_900, 0.0, apr, term, value_fn
    )  # 0 down + ~$1.9k fees/tax rolled in
    print(
        f"term {term} apr {apr}: months underwater {ne['months_underwater']}, max gap ${ne['max_gap']:,.0f}, gap@12 ${ne['gap_at_month_12']:,.0f}, gap@36 ${ne['gap_at_month_36']:,.0f}"
    )
print(
    "GAP exposure first 36 mo (84-mo, 0 down):",
    round(cv.gap_needed(price + 1_900, 0, 8.5, 84, value_fn)),
)
print(
    "20/4/10 ceiling for $7,000/mo gross income, insurance $180, fuel+maint $250:",
    {k: round(v) for k, v in cv.affordability_20_4_10(7_000, 7.0, 48, 20, 180, 250).items()},
)
# rolling $6,884 negative equity (Edmunds Q2-2026 average) into a new loan
roll = cv.loan_payment(50_089 + 6_884, 6.35, 70) - cv.loan_payment(50_089, 6.35, 70)
print(
    f"cost of rolling $6,884 negative equity at 6.35%/70 mo: +${roll:,.0f}/mo, +${roll * 70:,.0f} total"
)

# ---- 6. ownership economics ----------------------------------------------------------------------------------------------------
print("\n--- TCO / LEASE / EV ---")
t = cv.tco(
    price=31_500,
    years=5,
    miles_per_year=12_000,
    resale_value=31_500 * cv.retention_curve(5),
    apr_pct=6.9,
    down=6_300,
    loan_months=60,
    insurance_yr=2_000,
    fuel_cost_per_mile=0.13,
    maintenance_yr=600,
    registration_yr=150,
    repairs_yr=300,
    sales_tax_pct=6.0,
    fees=500,
)
print({k: round(v, 2) for k, v in t.items()})
lp = cv.lease_payment(
    36_000, 58, 36, 0.0027, cap_cost_reduction=2_000, acq_fee=695, tax_rate_pct=6.0
)
print({k: round(v, 4) for k, v in lp.items()})
lb = cv.lease_vs_buy(
    36_000,
    58,
    36,
    0.0027,
    2_000,
    6.9,
    2_000,
    buy_value_at_end=36_000 * cv.retention_curve(3),
    tax_rate_pct=6.0,
    invest_return_pct=4.0,
)
print({k: round(v) for k, v in lb.items()})
print(
    "EV vs ICE:",
    {k: round(v, 3) for k, v in cv.ev_vs_ice(12_000, 0.30, 0.17, 0.8, 0.45, 30, 4.10).items()},
)
print(
    "repair or replace:",
    cv.repair_or_replace(
        vehicle_value=9_000,
        repair_cost=2_800,
        expected_extra_years=3,
        replacement_monthly_cost=650,
        current_monthly_cost=200,
        expected_other_repairs_yr=700,
    ),
)

print("\n--- REBATE vs PROMO APR ($35,000, 60 mo, market APR 7.0%) ---")
for rb, pa in [(3_000, 0.0), (3_000, 3.9), (1_500, 0.0), (5_000, 0.0)]:
    r = cv.rebate_vs_low_apr(35_000, rb, 60, 7.0, pa)
    print(
        f"rebate ${rb:,} vs {pa}% APR ->",
        {k: (round(v) if isinstance(v, float) else v) for k, v in r.items()},
    )
assert cv.loan_payment(10_000, 0, 10) == 1_000
assert abs(cv.loan_payment(20_000, 6.0, 60) - 386.66) < 0.05
assert cv.retention_curve(0) == 1.0 and 0.50 < cv.retention_curve(5) < 0.62
print("\nALL ASSERTIONS PASSED")
