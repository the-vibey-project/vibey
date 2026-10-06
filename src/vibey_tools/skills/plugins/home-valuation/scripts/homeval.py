#!/usr/bin/env python3
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""
homeval.py - dependency-light (numpy + pandas) home valuation toolkit.

Functions are grouped by the skill that uses them:
  homeval-market-analysis-and-timing ...... market_stats(), months_of_supply(), absorption_rate()
  homeval-comps-adjustments-and-avms ...... score_comps(), adjust_comps(), reconcile(), hedonic_fit(),
                                            hedonic_predict(), price_band(), time_adjustment_pct_per_month()
  homeval-buyer-playbook / -seller-playbook  piti(), max_price_from_payment(), true_monthly_cost(),
                                            seller_net(), appraisal_gap_plan()
  homeval-diligence-risk-and-investment ... cap_rate(), grm(), cash_on_cash(), dscr(), brrrr(), rent_vs_buy()

NOT advice. Inputs are only as good as the comps you feed in.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# 1. MARKET STATISTICS
# ----------------------------------------------------------------------------


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def months_of_supply(active_listings: float, closed_last_12m: float) -> float:
    """Months of supply = active inventory / average monthly closed sales.
    Use pending sales (contracts) if you have them; closed sales lag 30-60 days.
    """
    monthly = closed_last_12m / 12.0
    return float("inf") if monthly == 0 else active_listings / monthly


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def absorption_rate(closed_last_n_months: float, n_months: float, active: float) -> dict:
    """Absorption = share of inventory that sells per month; inverse of MOS."""
    monthly = closed_last_n_months / n_months
    return {
        "monthly_sales": monthly,
        "absorption_pct_per_month": 100 * monthly / active if active else float("nan"),
        "months_of_supply": active / monthly if monthly else float("inf"),
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def classify_market(mos: float) -> str:
    """Rule-of-thumb thresholds (NAR/Redfin convention). Local variation is large."""
    if mos < 4:
        return "seller's market"
    if mos <= 6:
        return "balanced"
    return "buyer's market"


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def market_stats(sales: pd.DataFrame) -> dict:
    """Summarise a set of closed sales.
    Required columns: list_price, orig_list_price, sale_price, dom, sqft.
    """
    s = sales.copy()
    s["stl"] = s.sale_price / s.list_price  # sale-to-LAST-list
    s["stol"] = s.sale_price / s.orig_list_price  # sale-to-ORIGINAL-list (the honest one)
    s["ppsf"] = s.sale_price / s.sqft
    s["cut"] = s.list_price < s.orig_list_price
    return {
        "n": len(s),
        "median_price": float(s.sale_price.median()),
        "median_ppsf": float(s.ppsf.median()),
        "median_dom": float(s.dom.median()),
        "pct_sold_over_list": float((s.stl > 1).mean() * 100),
        "median_sale_to_list": float(s.stl.median() * 100),
        "median_sale_to_orig_list": float(s.stol.median() * 100),
        "pct_with_price_cut": float(s.cut.mean() * 100),
    }


# ----------------------------------------------------------------------------
# 2. COMPARABLE SALES
# ----------------------------------------------------------------------------


@dataclass
class Subject:
    sqft: float
    beds: int
    baths: float
    lot_sqft: float
    year_built: int
    condition: int  # 1 (poor) .. 5 (renovated) - your own consistent scale
    garage: int = 0  # bays
    has_pool: bool = False
    lat: float | None = None
    lon: float | None = None
    style: str = ""
    extras: dict = field(default_factory=dict)


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def haversine_miles(lat1, lon1, lat2, lon2) -> float:
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def score_comps(
    subject: Subject,
    comps: pd.DataFrame,
    today: pd.Timestamp,
    max_miles: float = 1.0,
    max_months: float = 6.0,
) -> pd.DataFrame:
    """Rank comps by similarity. Lower score = better comp.
    comps columns: sale_price, sale_date, sqft, beds, baths, lot_sqft, year_built,
                   condition, garage, has_pool, lat, lon, style
    Score is a transparent sum of normalised gaps (not a black box) so you can
    explain WHY a comp ranked where it did - appraisers must be able to.
    """
    c = comps.copy()
    c["miles"] = (
        [
            haversine_miles(subject.lat, subject.lon, la, lo)
            for la, lo in zip(c.lat, c.lon, strict=True)
        ]
        if subject.lat is not None
        else 0.0
    )
    c["months_ago"] = (today - pd.to_datetime(c.sale_date)).dt.days / 30.44
    c["gla_gap"] = (c.sqft - subject.sqft).abs() / subject.sqft  # 0.10 = 10% off
    c["age_gap"] = (c.year_built - subject.year_built).abs() / 20.0  # 20y = 1.0
    c["bed_gap"] = (c.beds - subject.beds).abs()
    c["bath_gap"] = (c.baths - subject.baths).abs()
    c["cond_gap"] = (c.condition - subject.condition).abs()
    c["lot_gap"] = (c.lot_sqft - subject.lot_sqft).abs() / max(subject.lot_sqft, 1)
    c["style_pen"] = (c["style"] != subject.style).astype(int) if subject.style else 0
    c["score"] = (
        2.0 * c.miles / max_miles
        + 1.5 * c.months_ago / max_months
        + 3.0 * c.gla_gap / 0.15  # GLA within 15% is the usual rule of thumb
        + 1.0 * c.age_gap
        + 0.75 * c.bed_gap
        + 0.75 * c.bath_gap
        + 2.0 * c.cond_gap / 2.0
        + 0.5 * c.lot_gap
        + 1.0 * c.style_pen
    )
    c["within_guardrails"] = (
        (c.miles <= max_miles) & (c.months_ago <= max_months) & (c.gla_gap <= 0.20)
    )
    return c.sort_values("score")


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def time_adjustment_pct_per_month(sales: pd.DataFrame) -> float:
    """Estimate market drift from the data itself: regress log(price/sqft) on months.
    Better than guessing; still noisy with < ~30 sales. Cross-check against a repeat-sale index.
    Needs: sale_price, sqft, sale_date.
    """
    d = sales.copy()
    d["t"] = (pd.to_datetime(d.sale_date) - pd.to_datetime(d.sale_date).min()).dt.days / 30.44
    y = np.log(d.sale_price / d.sqft)
    X = np.column_stack([np.ones(len(d)), d.t])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return float((math.exp(beta[1]) - 1) * 100)


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def adjust_comps(
    subject: Subject,
    comps: pd.DataFrame,
    today: pd.Timestamp,
    monthly_drift_pct: float = 0.0,
    ppsf_gla: float | None = None,
    bed_adj: float = 0.0,
    bath_adj: float = 7500.0,
    garage_bay_adj: float = 8000.0,
    pool_adj: float = 0.0,
    condition_step_adj: float | None = None,
    lot_per_sqft: float = 0.0,
    age_per_year: float = 0.0,
) -> pd.DataFrame:
    """Build the adjustment grid. Convention (USPAP/URAR): adjust the COMP toward the SUBJECT.
       - comp is SUPERIOR to subject  -> subtract (negative adjustment)
       - comp is INFERIOR to subject  -> add      (positive adjustment)
    Adjustment amounts must be MARKET-DERIVED (paired sales / regression / cost-to-cure),
    NOT cost-of-construction. Defaults here are placeholders to be overridden locally.
    GLA adjustment defaults to 40% of the comp's own $/sf (the marginal-sf rule of thumb:
    the last square foot is worth less than the average one).
    """
    c = comps.copy()
    months_ago = (today - pd.to_datetime(c.sale_date)).dt.days / 30.44
    out = pd.DataFrame(index=c.index)
    out["sale_price"] = c.sale_price
    out["time"] = c.sale_price * ((1 + monthly_drift_pct / 100) ** months_ago - 1)
    base = c.sale_price + out["time"]
    marginal = ppsf_gla if ppsf_gla is not None else 0.40 * (c.sale_price / c.sqft)
    out["gla"] = (subject.sqft - c.sqft) * marginal
    out["beds"] = (subject.beds - c.beds) * bed_adj
    out["baths"] = (subject.baths - c.baths) * bath_adj
    out["garage"] = (subject.garage - c.garage) * garage_bay_adj
    out["pool"] = (int(subject.has_pool) - c.has_pool.astype(int)) * pool_adj
    cstep = condition_step_adj if condition_step_adj is not None else 0.03 * base
    out["condition"] = (subject.condition - c.condition) * cstep
    out["lot"] = (subject.lot_sqft - c.lot_sqft) * lot_per_sqft
    out["age"] = (c.year_built - subject.year_built) * age_per_year  # newer comp -> subtract
    adj_cols = ["time", "gla", "beds", "baths", "garage", "pool", "condition", "lot", "age"]
    out["net_adj"] = out[adj_cols].sum(axis=1)
    out["gross_adj"] = out[adj_cols].abs().sum(axis=1)
    out["adjusted_price"] = c.sale_price + out["net_adj"]
    out["net_pct"] = 100 * out.net_adj / c.sale_price
    out["gross_pct"] = 100 * out.gross_adj / c.sale_price
    # Underwriting heuristics: net <= 15%, gross <= 25% (GSE guidance is a guideline, not a law)
    out["flag"] = np.where((out.net_pct.abs() > 15) | (out.gross_pct > 25), "OVER-ADJUSTED", "ok")
    return out


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def reconcile(adjusted: pd.DataFrame, scores: pd.Series | None = None, top_n: int = 3) -> dict:
    """Reconcile to a single opinion of value. NOT a plain average: weight the comps that
    needed the least adjustment. Returns the estimate and the evidence behind it."""
    a = adjusted.copy()
    a["w"] = 1.0 / (1.0 + a.gross_pct / 10.0)  # lower gross adj -> higher weight
    if scores is not None:
        a["w"] *= 1.0 / (1.0 + scores.loc[a.index])
    best = a.sort_values("gross_pct").head(top_n)
    w = best.w / best.w.sum()
    est = float((best.adjusted_price * w).sum())
    return {
        "estimate": est,
        "unweighted_median_all": float(a.adjusted_price.median()),
        "range_best": (float(best.adjusted_price.min()), float(best.adjusted_price.max())),
        "spread_pct": float(100 * (best.adjusted_price.max() - best.adjusted_price.min()) / est),
        "used": list(best.index),
    }


# ----------------------------------------------------------------------------
# 3. HEDONIC (REGRESSION) MODEL - the statistical cross-check
# ----------------------------------------------------------------------------


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def _design(df: pd.DataFrame, t_col: str = "t") -> np.ndarray:
    return np.column_stack(
        [
            np.ones(len(df)),
            np.log(df.sqft),
            df.beds,
            df.baths,
            np.log(df.lot_sqft),
            (2026 - df.year_built) / 10.0,
            df.condition,
            df.garage,
            df[t_col],
        ]
    )


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def hedonic_fit(sales: pd.DataFrame, as_of: pd.Timestamp) -> dict:
    """OLS on log(price). Coefficients on log(sqft) are elasticities; condition etc are %-effects.
    Returns coefficients, residual sd (in log points) and the fitted data for diagnostics.
    """
    d = sales.copy()
    d["t"] = (pd.to_datetime(d.sale_date) - as_of).dt.days / 30.44  # months relative to as_of (<=0)
    X, y = _design(d), np.log(d.sale_price.values)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = max(len(d) - X.shape[1], 1)
    sd = float(np.sqrt((resid**2).sum() / dof))
    # HC0 robust covariance for honest standard errors
    XtXi = np.linalg.pinv(X.T @ X)
    meat = X.T @ np.diag(resid**2) @ X
    cov = XtXi @ meat @ XtXi
    se = np.sqrt(np.diag(cov))
    names = [
        "const",
        "ln_sqft",
        "beds",
        "baths",
        "ln_lot",
        "age_decades",
        "condition",
        "garage",
        "months",
    ]
    r2 = 1 - (resid**2).sum() / ((y - y.mean()) ** 2).sum()
    return {
        "beta": dict(zip(names, beta, strict=True)),
        "se": dict(zip(names, se, strict=True)),
        "resid_sd_log": sd,
        "r2": float(r2),
        "n": len(d),
        "resid": resid,
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def hedonic_predict(model: dict, subject: Subject) -> dict:
    b = model["beta"]
    x = (
        b["const"]
        + b["ln_sqft"] * math.log(subject.sqft)
        + b["beds"] * subject.beds
        + b["baths"] * subject.baths
        + b["ln_lot"] * math.log(subject.lot_sqft)
        + b["age_decades"] * (2026 - subject.year_built) / 10.0
        + b["condition"] * subject.condition
        + b["garage"] * subject.garage
        + b["months"] * 0.0
    )
    point = math.exp(x)
    sd = model["resid_sd_log"]
    return {
        "point": point,
        "p10": point * math.exp(-1.2816 * sd),
        "p90": point * math.exp(1.2816 * sd),
        "approx_mdape_pct": 100 * 0.6745 * sd,
    }  # median abs % error ~ 0.6745 * sd for normal errors


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def price_band(estimate: float, off_market_error_pct: float = 7.2) -> tuple[float, float]:
    """Translate a published MEDIAN error into a band. Median error means HALF of estimates are
    worse than this - so treat +/- median error as a ~50% interval, and 2x as a ~80-90% one."""
    return (
        estimate * (1 - off_market_error_pct / 100),
        estimate * (1 + off_market_error_pct / 100),
    )


# ----------------------------------------------------------------------------
# 4. BUYER MATH
# ----------------------------------------------------------------------------


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def monthly_pi(loan: float, annual_rate_pct: float, years: int = 30) -> float:
    r = annual_rate_pct / 100 / 12
    n = years * 12
    return loan / n if r == 0 else loan * r / (1 - (1 + r) ** -n)


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def piti(
    price: float,
    down_pct: float,
    rate_pct: float,
    tax_rate_pct: float,
    insurance_annual: float,
    hoa_monthly: float = 0.0,
    pmi_rate_pct: float = 0.0,
    years: int = 30,
) -> dict:
    loan = price * (1 - down_pct / 100)
    pi = monthly_pi(loan, rate_pct, years)
    tax = price * tax_rate_pct / 100 / 12
    ins = insurance_annual / 12
    pmi = loan * pmi_rate_pct / 100 / 12 if down_pct < 20 else 0.0
    return {
        "loan": loan,
        "P&I": pi,
        "tax": tax,
        "insurance": ins,
        "HOA": hoa_monthly,
        "PMI": pmi,
        "total": pi + tax + ins + hoa_monthly + pmi,
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def max_price_from_payment(
    target_total: float,
    down_pct: float,
    rate_pct: float,
    tax_rate_pct: float,
    insurance_annual: float,
    hoa_monthly: float = 0.0,
    pmi_rate_pct: float = 0.0,
) -> float:
    lo, hi = 50_000.0, 5_000_000.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if (
            piti(
                mid, down_pct, rate_pct, tax_rate_pct, insurance_annual, hoa_monthly, pmi_rate_pct
            )["total"]
            > target_total
        ):
            hi = mid
        else:
            lo = mid
    return lo


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def true_monthly_cost(
    piti_total: float, price: float, maintenance_pct: float = 1.0, utilities_monthly: float = 0.0
) -> dict:
    """Add the costs lenders ignore. 1%/yr maintenance is the usual planning floor."""
    maint = price * maintenance_pct / 100 / 12
    return {
        "piti": piti_total,
        "maintenance_reserve": maint,
        "utilities": utilities_monthly,
        "all_in": piti_total + maint + utilities_monthly,
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def dti(front_housing: float, other_debts: float, gross_monthly_income: float) -> dict:
    return {
        "front_end_pct": 100 * front_housing / gross_monthly_income,
        "back_end_pct": 100 * (front_housing + other_debts) / gross_monthly_income,
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def appraisal_gap_plan(
    offer: float, appraised: float, down_payment: float, cash_reserve: float
) -> dict:
    """Lender lends against the LOWER of price or appraisal. Gap comes from your cash."""
    gap = max(offer - appraised, 0.0)
    return {
        "gap": gap,
        "covers_with_cash": gap <= cash_reserve,
        "options": [
            "renegotiate price",
            "cover gap in cash",
            "split gap with seller",
            "request reconsideration of value",
            "walk (if appraisal contingency intact)",
        ]
        if gap
        else ["no gap"],
    }


# ----------------------------------------------------------------------------
# 5. SELLER MATH
# ----------------------------------------------------------------------------


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def seller_net(
    price: float,
    mortgage_payoff: float,
    listing_comm_pct: float = 2.5,
    buyer_comm_pct: float = 2.5,
    seller_concessions_pct: float = 0.0,
    transfer_tax_pct: float = 0.0,
    title_escrow_pct: float = 0.5,
    prep_costs: float = 0.0,
    repairs_credit: float = 0.0,
    prorated_taxes_hoa: float = 0.0,
) -> dict:
    comm = price * (listing_comm_pct + buyer_comm_pct) / 100
    conc = price * seller_concessions_pct / 100
    xfer = price * transfer_tax_pct / 100
    title = price * title_escrow_pct / 100
    costs = comm + conc + xfer + title + prep_costs + repairs_credit + prorated_taxes_hoa
    net = price - mortgage_payoff - costs
    return {
        "gross": price,
        "commissions": comm,
        "concessions": conc,
        "transfer_tax": xfer,
        "title_escrow": title,
        "prep": prep_costs,
        "repairs_credit": repairs_credit,
        "prorations": prorated_taxes_hoa,
        "total_costs": costs,
        "costs_pct": 100 * costs / price,
        "net_proceeds": net,
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def carrying_cost_of_waiting(
    monthly_piti: float,
    monthly_utilities: float,
    months: float,
    price: float,
    monthly_drift_pct: float,
) -> dict:
    """Waiting for a better offer is not free. Compare carry vs expected price drift."""
    carry = (monthly_piti + monthly_utilities) * months
    drift = price * ((1 + monthly_drift_pct / 100) ** months - 1)
    return {"carry": carry, "expected_price_change": drift, "net_of_waiting": drift - carry}


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def home_sale_gain(
    sale_price: float,
    selling_costs: float,
    purchase_price: float,
    buying_costs: float,
    improvements: float,
    filing: str = "single",
) -> dict:
    """Federal 121 exclusion estimate ($250k/$500k). Educational only - ask a CPA."""
    basis = purchase_price + buying_costs + improvements
    gain = sale_price - selling_costs - basis
    excl = 500_000 if filing == "mfj" else 250_000
    return {
        "adjusted_basis": basis,
        "gain": gain,
        "exclusion": excl,
        "taxable_gain_before_rate": max(gain - excl, 0.0),
    }


# ----------------------------------------------------------------------------
# 6. INVESTMENT / INCOME APPROACH
# ----------------------------------------------------------------------------


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def noi(
    gross_scheduled_rent: float, vacancy_pct: float, opex: float, other_income: float = 0.0
) -> float:
    """NOI excludes debt service, depreciation, income tax and capex reserves (state your reserve separately)."""
    egi = gross_scheduled_rent * (1 - vacancy_pct / 100) + other_income
    return egi - opex


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def cap_rate(noi_annual: float, price: float) -> float:
    return 100 * noi_annual / price


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def value_from_cap(noi_annual: float, cap_pct: float) -> float:
    return noi_annual / (cap_pct / 100)


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def grm(price: float, gross_annual_rent: float) -> float:
    return price / gross_annual_rent


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def cash_on_cash(noi_annual: float, annual_debt_service: float, cash_invested: float) -> float:
    return 100 * (noi_annual - annual_debt_service) / cash_invested


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def dscr(noi_annual: float, annual_debt_service: float) -> float:
    return noi_annual / annual_debt_service


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def rent_vs_buy(
    price: float,
    down_pct: float,
    rate_pct: float,
    tax_rate_pct: float,
    insurance_annual: float,
    maintenance_pct: float,
    monthly_rent: float,
    years: int,
    appreciation_pct: float,
    rent_growth_pct: float,
    invest_return_pct: float,
    selling_cost_pct: float = 8.0,
    closing_cost_pct: float = 3.0,
) -> dict:
    """Opportunity-cost-aware comparison over `years`.
    Renter starts by investing what the buyer would have spent up front (down + closing costs).
    Each month both parties spend the same total cash: whoever has the cheaper path invests the difference.
    Buyer net worth = home equity after selling costs + buyer's invested surplus (if any).
    Renter net worth = portfolio. Ignores taxes on investment gains and the mortgage-interest deduction;
    state/federal tax effects can move the break-even by years - ask a CPA."""
    p = piti(price, down_pct, rate_pct, tax_rate_pct, insurance_annual)
    r = rate_pct / 100 / 12
    pay = p["P&I"]
    bal = p["loan"]
    upfront = price * down_pct / 100 + price * closing_cost_pct / 100
    renter_port, buyer_port = upfront, 0.0
    g = (1 + invest_return_pct / 100) ** (1 / 12) - 1
    rent, val = monthly_rent, price
    for m in range(1, years * 12 + 1):
        bal = max(bal * (1 + r) - pay, 0.0)
        val *= (1 + appreciation_pct / 100) ** (1 / 12)
        if m > 1 and (m - 1) % 12 == 0:
            rent *= 1 + rent_growth_pct / 100
        own_cost = (
            pay
            + price * tax_rate_pct / 100 / 12
            + insurance_annual / 12
            + price * maintenance_pct / 100 / 12
        )
        renter_port *= 1 + g
        buyer_port *= 1 + g
        diff = own_cost - rent
        if diff > 0:
            renter_port += diff
        else:
            buyer_port += -diff
    equity = val * (1 - selling_cost_pct / 100) - bal
    return {
        "buy_net_worth": equity + buyer_port,
        "rent_net_worth": renter_port,
        "home_value_end": val,
        "loan_balance_end": bal,
        "equity_after_sale": equity,
        "winner": "buy" if equity + buyer_port > renter_port else "rent",
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def brrrr(
    purchase: float,
    rehab: float,
    arv: float,
    refi_ltv_pct: float,
    monthly_rent: float,
    opex_pct_of_rent: float,
    rate_pct: float,
    holding_costs: float = 0.0,
) -> dict:
    """Buy-Rehab-Rent-Refinance-Repeat sanity check. All-in cost vs ARV and cash left in the deal."""
    all_in = purchase + rehab + holding_costs
    refi_loan = arv * refi_ltv_pct / 100
    cash_left = all_in - refi_loan
    noi_a = monthly_rent * 12 * (1 - opex_pct_of_rent / 100)
    ds = monthly_pi(refi_loan, rate_pct) * 12
    return {
        "all_in": all_in,
        "all_in_pct_of_arv": 100 * all_in / arv,
        "refi_loan": refi_loan,
        "cash_left_in_deal": cash_left,
        "noi": noi_a,
        "debt_service": ds,
        "dscr": noi_a / ds if ds else float("inf"),
        "cash_flow": noi_a - ds,
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def seventy_percent_rule_max_offer(arv: float, rehab: float, pct: float = 70.0) -> float:
    """Flipper's heuristic: max offer = ARV*70% - rehab. A screen, not a valuation."""
    return arv * pct / 100 - rehab


if __name__ == "__main__":
    print("homeval toolkit loaded. Run test_homeval.py for the worked example.")
