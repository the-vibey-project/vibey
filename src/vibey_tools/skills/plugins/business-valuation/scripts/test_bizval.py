#!/usr/bin/env python3
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Worked examples + self-tests for bizval.py. Synthetic data with KNOWN ground truth. Run: python3 test_bizval.py"""

import math

import bizval as bv
import numpy as np
import pandas as pd

rng = np.random.default_rng(11)
pd.set_option("display.width", 200)

# ---------------------------------------------------------------------------------------------------------
print(
    "=== 1. MARKET APPROACH: synthetic private-company transactions with a KNOWN multiple function ==="
)


# Module-level by design (ADR-0016): the toolkit's self-test, run as a plain script.
def true_mult(ebitda_m, growth, margin, recurring, top):
    return math.exp(
        1.25
        + 0.20 * math.log(ebitda_m)
        + 1.2 * growth
        + 0.8 * margin
        + 0.35 * recurring
        - 0.9 * top
    )


N = 220
d = pd.DataFrame(
    {
        "ebitda": np.exp(rng.uniform(math.log(1.0), math.log(30.0), N)),  # $M
        "growth": rng.normal(0.07, 0.05, N).clip(-0.10, 0.30),
        "margin": rng.normal(0.16, 0.06, N).clip(0.04, 0.40),
        "recurring": rng.uniform(0, 0.8, N),
        "top_customer": rng.uniform(0.03, 0.5, N),
    }
)
d["true_mult"] = [
    true_mult(r.ebitda, r.growth, r.margin, r.recurring, r.top_customer) for r in d.itertuples()
]
d["ev"] = (
    d.ebitda * d.true_mult * np.exp(rng.normal(0, 0.12, N))
)  # observed price has deal-specific noise
d["multiple"] = d.ev / d.ebitda
st = bv.comps_stats(d.multiple)
print(
    f"all-comps multiple: median {st['median']:.2f}x  IQR {st['q1']:.2f}-{st['q3']:.2f}x  harmonic mean {st['harmonic_mean']:.2f}x  (n={st['n']})"
)
model = bv.fit_multiple_model(d)
b = model["beta"]
print(
    f"hedonic fit: R2={model['r2']:.3f} resid sd={model['resid_sd']:.3f}; ln_ebitda={b['ln_ebitda']:.2f} (truth 0.20), growth={b['growth']:.2f} (1.2), "
    f"margin={b['margin']:.2f} (0.8), recurring={b['recurring']:.2f} (0.35), top_customer={b['top_customer']:.2f} (-0.9)"
)
assert abs(b["ln_ebitda"] - 0.20) < 0.04 and abs(b["top_customer"] + 0.9) < 0.25

errs = {"median multiple (all comps)": [], "size-band median (EBITDA +/-50%)": [], "regression": []}
for _ in range(150):
    s = dict(
        ebitda=float(np.exp(rng.uniform(math.log(1.2), math.log(25)))),
        growth=float(rng.normal(0.07, 0.05)),
        margin=float(rng.normal(0.16, 0.05)),
        recurring=float(rng.uniform(0, 0.8)),
        top=float(rng.uniform(0.03, 0.5)),
    )
    tv = true_mult(s["ebitda"], s["growth"], s["margin"], s["recurring"], s["top"]) * s["ebitda"]
    band = d[(d.ebitda > s["ebitda"] * 0.5) & (d.ebitda < s["ebitda"] * 1.5)]
    e1 = d.multiple.median() * s["ebitda"]
    e2 = (band.multiple.median() if len(band) >= 5 else d.multiple.median()) * s["ebitda"]
    e3 = bv.predict_multiple(
        model, s["ebitda"], s["growth"], s["margin"], s["recurring"], s["top"]
    )["ev"]
    for k, v in zip(errs, [e1, e2, e3], strict=True):
        errs[k].append(abs(v - tv) / tv * 100)
print("Median / 90th-percentile abs error in EV over 150 random subjects:")
for k, v in errs.items():
    print(f"  {k:36s} {np.median(v):5.1f}%  /  {np.percentile(v, 90):5.1f}%")
assert (
    np.median(errs["regression"])
    < np.median(errs["size-band median (EBITDA +/-50%)"])
    < np.median(errs["median multiple (all comps)"])
)

# ---------------------------------------------------------------------------------------------------------
print("\n=== 2. EARNINGS NORMALIZATION (Main Street) ===")
s = bv.sde(
    net_income=60_000,
    owner_comp=95_000,
    interest=8_000,
    taxes=0,
    depreciation_amort=22_000,
    one_time_expenses=9_000,
    personal_expenses=14_000,
    other_addbacks=0,
    one_time_income=6_000,
)
print("SDE =", s, "  (60+95+8+22+9+14-6 = 202k)")
assert s == 202_000
accepted = bv.quality_weighted_addbacks([(9_000, 0.9), (14_000, 0.5), (12_000, 0.2)])
print(
    f"quality-weighted add-backs: ${accepted:,.0f} of $35,000 claimed -> buyer-accepted SDE ~ ${60_000 + 95_000 + 8_000 + 22_000 - 6_000 + accepted:,.0f}"
)
print(
    "3-yr weighted-average earnings (100k, 120k, 150k; weights 1-2-3):",
    round(bv.weighted_average_earnings([100_000, 120_000, 150_000])),
)
print(
    "Median-deal check: price $349,250 / median cash flow $155,921 =",
    round(349_250 / 155_921, 2),
    "x  (BizBuySell reports ~2.7x average of individual multiples)",
)

# ---------------------------------------------------------------------------------------------------------
print("\n=== 3. INCOME APPROACH ===")
# identity: growing perpetuity
cfs = [100 * 1.03**t for t in range(0, 5)]  # CF1..CF5 growing at 3%
ev = bv.dcf(cfs, 0.11, terminal_growth=0.03)["ev"]
closed = cfs[0] / (0.11 - 0.03)
print(f"DCF identity: explicit+Gordon EV = {ev:.4f}  closed-form CF1/(r-g) = {closed:.4f}")
assert abs(ev - closed) < 1e-6
# cap-of-earnings equals
assert abs(bv.capitalized_earnings(100, 0.11, 0.03) - 100 * 1.03 / 0.08) < 1e-9
print(
    "implied discount rate for price 1,287.5 on CF0=100,g=3%:",
    round(bv.implied_discount_rate(1287.5, 103, 0.03), 4),
)

rf, erp = (
    0.056,
    0.050,
)  # rf ~ spot 20y UST (placeholder ~5.6% on Oct 6 2026; VERIFY); Kroll recommended US ERP 5.0%
ke = bv.capm_cost_of_equity(rf, erp, beta=1.1, size_premium=0.02, company_specific=0.02)
w = bv.wacc(ke, cost_debt_pre_tax=0.10, debt_weight=0.30, tax_rate=0.25)
print(
    f"cost of equity {ke:.2%}; WACC {w:.2%}  (rf 5.6%, ERP 5.0%, beta 1.1, size 2%, specific 2%, Kd 10% pre-tax, 30% debt, 25% tax)"
)
ub = bv.unlever_beta(1.25, 0.40, 0.25)
print(
    "unlever 1.25 at D/E 0.4:",
    round(ub, 3),
    "-> relever at D/E 0.43:",
    round(bv.relever_beta(ub, 0.43, 0.25), 3),
)

# a $3.0M-EBITDA business, 6% growth for 5 years
cash = []
e = 3.0
for _year in range(1, 6):
    e *= 1.06
    cash.append(
        bv.fcff(
            ebitda=e,
            da=0.30 * e / 3.0 * 1.0,
            capex=0.33 * e / 3.0,
            delta_nwc=0.06 * e / 3.0,
            tax_rate=0.25,
        )
    )
cash = [round(c, 4) for c in cash]
res = bv.dcf(cash, w, terminal_growth=0.03)
print("FCFF ($M):", cash)
print(
    f"DCF EV at WACC {w:.1%}, g 3%: ${res['ev']:.2f}M  = {res['ev'] / 3.0:.2f}x current EBITDA; TV share {res['tv_share']:.0%}; implied exit multiple on yr-5 EBITDA {res['implied_exit_multiple'] / (3.0 * 1.06**5) if False else res['terminal_value'] / (3.0 * 1.06**5):.2f}x"
)
print(bv.dcf_sensitivity(cash, [w - 0.02, w, w + 0.02], [0.02, 0.03, 0.04]).round(2).to_string())
low = bv.dcf(cash, w - 0.013, terminal_growth=0.03)["ev"]
print(
    f"if discount rate were 1.3 points lower (e.g., rf 4.3% instead of 5.6%): EV ${low:.2f}M vs ${res['ev']:.2f}M -> {100 * (low / res['ev'] - 1):+.1f}%"
)
assert low > res["ev"]
print(
    "discounts:",
    {
        k: (round(v, 1) if isinstance(v, float) else v)
        for k, v in bv.apply_discounts(1000, minority_pct=0, dlom_pct=25, key_person_pct=10).items()
        if k != "steps"
    },
)
print(
    "control premium implied by a 20% minority discount:",
    round(bv.control_premium_from_minority_discount(0.20), 3),
)
print(
    "EV->equity:",
    bv.ev_to_equity(
        5_000_000, debt=600_000, cash=250_000, debt_like=150_000, nwc_shortfall=100_000
    ),
)

# ---------------------------------------------------------------------------------------------------------
print("\n=== 4. DEAL STRUCTURE: headline vs present value to the seller ===")
p = bv.deal_pv(
    cash_at_close=3_000_000,
    seller_note=1_000_000,
    note_rate=0.06,
    note_years=5,
    earnout_max=500_000,
    earnout_prob=0.40,
    earnout_year=2,
    rollover_value=500_000,
    rollover_haircut=0.25,
    discount_rate=0.12,
    escrow=250_000,
)
print({k: round(v, 3) if v < 10 else round(v) for k, v in p.items()})
alt = bv.deal_pv(cash_at_close=4_300_000, discount_rate=0.12)
print(
    f"vs an all-cash $4.3M bid: PV ${alt['pv']:,.0f}   |  the $5.25M structured headline is worth ${p['pv']:,.0f} to the seller ({p['pv_pct_of_headline']:.0%} of headline)"
)
assert p["pv"] < p["headline"] * 0.9

print("\n=== 5. FINANCING: SBA-style debt capacity and sources & uses ===")
cf = (
    155_921 - 70_000
)  # median cash flow of sold small businesses less a placeholder buyer-salary draw
mp = bv.max_price_for_dscr(
    cf, min_dscr=1.25, apr=0.10, years=10, equity_pct=0.10, other_costs_pct=0.03
)
print(
    f"cash flow for debt service ${cf:,.0f} -> max debt service ${mp['max_annual_debt_service']:,.0f}/yr -> max loan ${mp['max_loan']:,.0f} -> max PRICE ${mp['max_price']:,.0f} "
    f"(equity needed ${mp['equity_needed']:,.0f}); at 10%/10y payment factor {bv.loan_payment(1, 0.10, 10) * 12:.4f}/yr"
)
mp8 = bv.max_price_for_dscr(cf, 1.25, 0.08, 10)
print(
    f"same business at an 8.0% loan rate: max price ${mp8['max_price']:,.0f} (+{100 * (mp8['max_price'] / mp['max_price'] - 1):.0f}%)  <- rate sensitivity of what buyers can pay"
)
su = bv.sba_sources_uses(349_250, fees_and_costs=12_000)
print({k: round(v, 3) if v < 5 else round(v) for k, v in su.items()})
print(
    "DSCR on median deal if loan = SBA amount, 10%/10y, CF after draw:",
    round(bv.dscr(cf, bv.loan_payment(su["sba_loan"], 0.10, 10) * 12), 2),
)

print("\nLBO sensitivity (entry 7.0x TTM EBITDA, 4.5x debt, 6% growth, exit 7.0x, 5 yrs):")
for rate in [0.06, 0.08, 0.10, 0.12]:
    r = bv.lbo(10.0, 7.0, 4.5, rate, 0.06, 5, 7.0)
    print(
        f"  debt cost {rate:.0%}: MOIC {r['moic']:.2f}x  IRR {r['irr']:.1%}  debt at exit {r['debt_at_exit']:.1f}"
    )
r6, r10 = bv.lbo(10.0, 7.0, 4.5, 0.06, 0.06, 5, 7.0), bv.lbo(10.0, 7.0, 4.5, 0.10, 0.06, 5, 7.0)
assert r6["irr"] > r10["irr"]
rx = bv.lbo(10.0, 7.0, 4.5, 0.10, 0.06, 5, 6.0)
print(f"  at 10% debt with exit multiple 6.0x (one turn lower): IRR {rx['irr']:.1%}")
cfl = [-100, 0, 0, 0, 0, 200]
print("IRR check [-100,...,+200 in 5y] =", round(bv.irr(cfl), 4), "(truth 14.87%)")
assert abs(bv.irr(cfl) - (2**0.2 - 1)) < 1e-4

# ---------------------------------------------------------------------------------------------------------
print("\n=== 6. TAX: asset vs stock; QSBS ===")
t = bv.asset_vs_stock(
    price=5_000_000, stock_basis=800_000, ordinary_recapture=600_000, inventory_ar_ordinary=400_000
)
print({k: round(v) if abs(v) > 100 else round(v, 2) for k, v in t.items()})
print("QSBS ($12M gain, issued after 7/4/2025):")
for yrs in [2.9, 3, 4, 5]:
    q = bv.qsbs_exclusion(12_000_000, yrs, True)
    print(
        f"  hold {yrs}y: exclusion {q['exclusion_pct']:.0%}, taxable ${q['taxable_gain']:,.0f}, federal tax ${q['federal_tax']:,.0f} ({q['effective_rate']:.1%})"
    )
q_old = bv.qsbs_exclusion(12_000_000, 4, False)
print(
    f"  pre-OBBBA stock held 4y: exclusion {q_old['exclusion_pct']:.0%}, tax ${q_old['federal_tax']:,.0f}"
)
q_big = bv.qsbs_exclusion(40_000_000, 5, True, basis=1_000_000)
print(
    f"  $40M gain at 5y: excluded ${q_big['excluded_gain']:,.0f} (cap $15M), taxable ${q_big['taxable_gain']:,.0f}"
)
assert bv.qsbs_exclusion(12_000_000, 5, True)["federal_tax"] == 0

# ---------------------------------------------------------------------------------------------------------
print("\n=== 7. STARTUPS ===")
pr = bv.post_money_round(pre_money=12_000_000, raise_amt=3_000_000, option_pool_topup_pct_post=0.05)
print({k: round(v, 4) if v < 5 else round(v) for k, v in pr.items()})
sf = bv.safe_post_money_conversion(500_000, 10_000_000, round_pre_money=12_000_000)
print(
    f"post-money SAFE $500k at $10M cap: {sf['cap_ownership_pct_before_new_money']:.1%} before new money; converts at {sf['converts_at']}"
)
vm = bv.venture_method(
    exit_value=300_000_000, years=7, target_multiple=10, expected_dilution=0.50, raise_amt=3_000_000
)
print(
    f"venture method: $300M exit, 50% later dilution, 10x target -> post-money ${vm['post_money'] / 1e6:.1f}M, pre ${vm['pre_money'] / 1e6:.1f}M (target IRR {vm['target_irr']:.1%})"
)
assert abs(vm["post_money"] - 15_000_000) < 1

# ---------------------------------------------------------------------------------------------------------
print("\n=== 8. NON-PROFIT: financial health, stress, adjusted net assets, SROI ===")
r = bv.np_ratios(
    total_revenue=4_000_000,
    government_grants=1_800_000,
    contributions=1_400_000,
    program_fees=600_000,
    other_revenue=200_000,
    total_expenses=3_900_000,
    program_expenses=3_200_000,
    fundraising_expenses=350_000,
    mgmt_general_expenses=350_000,
    cash_and_equivalents=520_000,
    investments_liquid=100_000,
    receivables=600_000,
    current_liabilities=500_000,
    total_assets=2_300_000,
    total_liabilities=900_000,
    net_assets_without_restrictions=1_300_000,
    net_ppe=800_000,
    debt=400_000,
)
print({k: (round(v, 3) if abs(v) < 100 else round(v)) for k, v in r.items()})
print(
    "-> program ratio 82% looks healthy, but months of cash",
    round(r["months_of_cash"], 1),
    "and LUNA",
    round(r["months_of_luna"], 1),
    "months with 45% government dependence = fragile",
)
assert r["program_expense_ratio"] > 0.8 and r["months_of_luna"] < 2

# stress: lose 30% of government grants (=$540k/yr) starting month 3, reimbursement lag; expenses 325k/mo, revenue 333k/mo
base = bv.np_runway(
    cash=520_000,
    monthly_expenses=325_000,
    monthly_recurring_revenue=333_000,
    receivables_30_60=0,
    months=18,
)
stress = bv.np_runway(
    cash=520_000, monthly_expenses=325_000, monthly_recurring_revenue=333_000 - 45_000, months=18
)
print(
    "cash at month 12: base",
    round(base.cash.iloc[11]),
    "| stress",
    round(stress.cash.iloc[11]),
    "| month 18: stress",
    round(stress.cash.iloc[-1]),
    " | first negative month:",
    int(stress[stress.cash < 0].month.min()) if (stress.cash < 0).any() else None,
)
an = bv.np_adjusted_net_assets(
    total_assets_book=2_300_000,
    liabilities_book=900_000,
    fair_value_adjustments=350_000,
    donor_restricted_perpetual=0,
    restricted_time_purpose=300_000,
    contingent_liabilities=120_000,
    deferred_maintenance=180_000,
)
print(
    "book net assets $1,400,000 -> fair-value net assets",
    round(an["fair_value_net_assets"]),
    " -> unencumbered",
    round(an["unencumbered_net_assets"]),
)
sr = bv.sroi(
    [
        {
            "quantity": 220,
            "proxy_value": 4_500,
            "deadweight": 0.30,
            "attribution": 0.20,
            "displacement": 0.0,
            "drop_off": 0.20,
            "years": 3,
        },
        {
            "quantity": 220,
            "proxy_value": 1_200,
            "deadweight": 0.15,
            "attribution": 0.10,
            "years": 2,
        },
    ],
    investment=620_000,
    discount_rate=0.035,
)
print(
    f"SROI: PV of social value ${sr['pv_social_value']:,.0f} on ${sr['investment']:,.0f} -> {sr['sroi_ratio']:.2f} : 1  (proxy values are judgments; show a range)"
)
lo = bv.sroi(
    [
        {
            "quantity": 220,
            "proxy_value": 2_700,
            "deadweight": 0.50,
            "attribution": 0.30,
            "drop_off": 0.30,
            "years": 3,
        }
    ],
    620_000,
)
print(f"  pessimistic single-outcome case: {lo['sroi_ratio']:.2f} : 1")

assert abs(bv.loan_payment(100_000, 0.0, 10) - 100_000 / 120) < 1e-6
print("\nALL ASSERTIONS PASSED")
