#!/usr/bin/env python3
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""
carval.py - dependency-light (numpy + pandas) toolkit for valuing, buying and selling cars.

  carval-valuing-a-specific-vehicle ... score_listings(), adjust_listings(), reconcile(), hedonic_fit(),
                                         hedonic_predict(), mileage_adjustment_per_mile(), price_band()
  carval-market-analysis-and-timing ... days_supply(), retention_curve(), seasonal_note()
  carval-buyer-playbook ............... loan_payment(), amortization(), otd_price(), negative_equity_months(),
                                         gap_needed(), term_comparison(), affordability_20_4_10()
  carval-seller-playbook .............. channel_values(), sell_net(), tradein_tax_credit_value()
  carval-diligence-risk-and-ownership-economics
                                     ... tco(), lease_payment(), lease_vs_buy(), ev_vs_ice(), repair_or_replace()

NOT advice. Default percentages are PLACEHOLDERS to be replaced with local, vehicle-specific evidence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# 1. MARKET / DEPRECIATION HELPERS
# ----------------------------------------------------------------------------


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def days_supply(units_in_stock: float, units_sold_last_30d: float) -> float:
    """Days' supply = inventory / (sales per day). ~30-45 is balanced for used retail (conventions vary);
    note the calendar: dealers count it differently for new vs used."""
    daily = units_sold_last_30d / 30.0
    return float("inf") if daily == 0 else units_in_stock / daily


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def retention_curve(
    age_years: float, floor: float = 0.10, first_year_drop: float = 0.15, k: float = 0.11
) -> float:
    """Fraction of new price retained at `age_years`: a first-year step drop then exponential decay to a floor.
    Placeholder shape. Typical 5-year retention is ~58% (average 5-yr depreciation ~41.8%, iSeeCars Mar-2025..Feb-2026),
    with enormous model-level dispersion (best ~10-25%, EVs/luxury worst). Calibrate with data for YOUR model."""
    if age_years <= 0:
        return 1.0
    step = (1 - first_year_drop) if age_years >= 1 else 1 - first_year_drop * age_years
    decay = math.exp(-k * max(age_years - 1, 0))
    return floor + (step - floor) * decay


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def mileage_expected(age_years: float, miles_per_year: float = 12_000) -> float:
    return age_years * miles_per_year


# ----------------------------------------------------------------------------
# 2. VALUING A SPECIFIC VEHICLE FROM COMPARABLE LISTINGS / SALES
# ----------------------------------------------------------------------------


@dataclass
class Vehicle:
    year: int
    miles: float
    trim: str
    condition: int  # 1 (poor) .. 5 (excellent) on YOUR consistent scale
    owners: int = 1
    accidents: int = 0  # reported
    cpo: bool = False
    options_value: float = 0.0  # market-value of options NOT captured by trim (use evidence)


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def score_listings(
    subject: Vehicle,
    comps: pd.DataFrame,
    today: pd.Timestamp,
    max_miles_gap: float = 25_000,
    max_days: int = 90,
) -> pd.DataFrame:
    """Rank comparable listings/sales. Lower score = better comp.
    Columns required: price, year, miles, trim, condition, owners, accidents, cpo, list_date, status('sold'|'active'), region_ok(bool)
    """
    c = comps.copy()
    c["days_old"] = (today - pd.to_datetime(c.list_date)).dt.days
    c["year_gap"] = (c.year - subject.year).abs()
    c["miles_gap"] = (c.miles - subject.miles).abs() / max_miles_gap
    c["trim_pen"] = (c["trim"] != subject.trim).astype(int)
    c["cond_gap"] = (c.condition - subject.condition).abs()
    c["acc_gap"] = (c.accidents - subject.accidents).abs()
    c["cpo_pen"] = (c.cpo != subject.cpo).astype(int)
    c["score"] = (
        3.0 * c.year_gap
        + 2.0 * c.miles_gap
        + 4.0 * c.trim_pen
        + 2.0 * c.cond_gap
        + 1.0 * c.acc_gap
        + 1.5 * c.cpo_pen
        + 1.0 * c.days_old / max_days
        + 3.0 * (~c.region_ok).astype(int)
    )
    c["within_guardrails"] = (
        (c.year_gap <= 1)
        & (c.trim_pen == 0)
        & (c.miles_gap <= 1.0)
        & (c.days_old <= max_days)
        & (c.cond_gap <= 1)
        & c.region_ok
    )
    return c.sort_values("score")


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def mileage_adjustment_per_mile(comps: pd.DataFrame) -> float:
    """Estimate $/mile from the comps themselves (within one trim & year band):
    slope of price on miles, controlling for year via simple demeaning. Use only with >= ~15 comps.
    Typical order of magnitude for mainstream cars is cents per mile (rises with value)."""
    d = comps.copy()
    d["miles_c"] = d.miles - d.groupby("year").miles.transform("mean")
    d["price_c"] = d.price - d.groupby("year").price.transform("mean")
    denom = (d.miles_c**2).sum()
    return float((d.miles_c * d.price_c).sum() / denom) if denom else 0.0


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def adjust_listings(
    subject: Vehicle,
    comps: pd.DataFrame,
    today: pd.Timestamp,
    per_mile: float,
    ask_to_sale_discount_pct: float = 3.0,
    condition_step_pct: float = 3.0,
    accident_pct: float = 6.0,
    owner_step_pct: float = 1.0,
    cpo_premium: float = 1_500.0,
    monthly_drift_pct: float = 0.0,
    year_step_pct: float = 7.0,
) -> pd.DataFrame:
    """Adjust each comp TOWARD the subject (comp superior -> subtract; comp inferior -> add).
    - Active listings are ASKING prices: convert to expected transaction price with ask_to_sale_discount_pct
      (placeholder; calibrate from sold/asking ratios in your market). Sold comps get no discount.
    - Mileage: (comp miles - subject miles) * per_mile  (a higher-mile comp is worth less -> add if comp has MORE miles).
    - Condition/accident/ownership/CPO as percentages (placeholders; verify with paired comps).
    - Year: percent per model-year difference (newer comp is superior -> subtract).
    """
    c = comps.copy()
    out = pd.DataFrame(index=c.index)
    out["price"] = c.price
    base = c.price * np.where(c.status == "active", 1 - ask_to_sale_discount_pct / 100, 1.0)
    out["ask_to_sale"] = base - c.price
    days = (today - pd.to_datetime(c.list_date)).dt.days
    out["time"] = base * ((1 + monthly_drift_pct / 100) ** (days / 30.44) - 1)
    b = base + out["time"]
    out["miles"] = (c.miles - subject.miles) * per_mile
    out["year"] = (subject.year - c.year) * b * year_step_pct / 100
    out["condition"] = (subject.condition - c.condition) * b * condition_step_pct / 100
    out["accident"] = (c.accidents - subject.accidents) * b * accident_pct / 100
    out["owners"] = (c.owners - subject.owners) * b * owner_step_pct / 100
    out["cpo"] = (int(subject.cpo) - c.cpo.astype(int)) * cpo_premium
    out["options"] = subject.options_value
    cols = ["ask_to_sale", "time", "miles", "year", "condition", "accident", "owners", "cpo"]
    out["net_adj"] = out[cols].sum(axis=1) + out["options"]
    out["gross_adj"] = out[cols].abs().sum(axis=1)
    out["adjusted_price"] = c.price + out.net_adj
    out["net_pct"] = 100 * out.net_adj / c.price
    out["gross_pct"] = 100 * out.gross_adj / c.price
    out["flag"] = np.where(out.gross_pct > 20, "OVER-ADJUSTED", "ok")
    return out


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def reconcile(adjusted: pd.DataFrame, top_n: int = 4) -> dict:
    a = adjusted.copy()
    a["w"] = 1.0 / (1.0 + a.gross_pct / 5.0)
    best = a.sort_values("gross_pct").head(top_n)
    w = best.w / best.w.sum()
    est = float((best.adjusted_price * w).sum())
    return {
        "estimate": est,
        "range_best": (float(best.adjusted_price.min()), float(best.adjusted_price.max())),
        "spread_pct": float(100 * (best.adjusted_price.max() - best.adjusted_price.min()) / est),
        "unweighted_median_all": float(a.adjusted_price.median()),
        "used": list(best.index),
    }


# ---- Hedonic regression -------------------------------------------------------------------------------


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def _X(df: pd.DataFrame, trims: list[str]) -> np.ndarray:
    cols = [
        np.ones(len(df)),
        df.age.values,
        df.miles.values / 10_000.0,
        df.condition.values,
        df.accidents.values,
        df.owners.values,
        df.months.values,
    ]
    for t in trims[1:]:
        cols.append((df["trim"] == t).astype(float).values)
    return np.column_stack(cols)


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def hedonic_fit(sales: pd.DataFrame, as_of: pd.Timestamp) -> dict:
    """ln(price) = b0 + b1*age + b2*(miles/10k) + b3*condition + b4*accidents + b5*owners + b6*months + trim dummies.
    Needs columns: price, year, miles, trim, condition, accidents, owners, list_date. Use ONE model/generation."""
    d = sales.copy()
    d["age"] = as_of.year - d.year + 0.0
    d["months"] = (pd.to_datetime(d.list_date) - as_of).dt.days / 30.44
    trims = sorted(d["trim"].unique().tolist())
    X, y = _X(d, trims), np.log(d.price.values)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = max(len(d) - X.shape[1], 1)
    sd = float(np.sqrt((resid**2).sum() / dof))
    names = ["const", "age", "per10k_miles", "condition", "accidents", "owners", "months"] + [
        f"trim_{t}" for t in trims[1:]
    ]
    return {
        "beta": dict(zip(names, beta, strict=True)),
        "trims": trims,
        "resid_sd_log": sd,
        "n": len(d),
        "r2": float(1 - (resid**2).sum() / ((y - y.mean()) ** 2).sum()),
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def hedonic_predict(model: dict, v: Vehicle, as_of: pd.Timestamp) -> dict:
    b = model["beta"]
    x = (
        b["const"]
        + b["age"] * (as_of.year - v.year)
        + b["per10k_miles"] * v.miles / 10_000
        + b["condition"] * v.condition
        + b["accidents"] * v.accidents
        + b["owners"] * v.owners
    )
    if f"trim_{v.trim}" in b:
        x += b[f"trim_{v.trim}"]
    p = math.exp(x) + v.options_value
    sd = model["resid_sd_log"]
    return {
        "point": p,
        "p10": p * math.exp(-1.2816 * sd),
        "p90": p * math.exp(1.2816 * sd),
        "approx_mdape_pct": 100 * 0.6745 * sd,
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def price_band(estimate: float, pct: float) -> tuple[float, float]:
    return estimate * (1 - pct / 100), estimate * (1 + pct / 100)


# ----------------------------------------------------------------------------
# 3. SELLING CHANNELS
# ----------------------------------------------------------------------------


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def channel_values(
    retail_value: float,
    private_party_disc_pct: float = 6.0,
    instant_offer_disc_pct: float = 14.0,
    tradein_disc_pct: float = 16.0,
    wholesale_disc_pct: float = 20.0,
) -> dict:
    """Illustrative chain from a dealer-retail value down to wholesale. THE DISCOUNTS ARE PLACEHOLDERS:
    the spread varies by vehicle, age, condition, region and market (it narrows when used-car demand is hot
    and widens when wholesale softens). Replace with real quotes (§22)."""
    return {
        "retail": retail_value,
        "private_party": retail_value * (1 - private_party_disc_pct / 100),
        "instant_offer": retail_value * (1 - instant_offer_disc_pct / 100),
        "dealer_tradein": retail_value * (1 - tradein_disc_pct / 100),
        "wholesale": retail_value * (1 - wholesale_disc_pct / 100),
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def tradein_tax_credit_value(
    trade_value: float, sales_tax_rate_pct: float, state_gives_credit: bool = True
) -> float:
    """In states that tax only the net-of-trade price, a trade-in saves tax: trade_value * rate."""
    return trade_value * sales_tax_rate_pct / 100 if state_gives_credit else 0.0


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def sell_net(
    channel: str,
    price: float,
    payoff: float = 0.0,
    listing_cost: float = 0.0,
    prep_cost: float = 0.0,
    tax_credit: float = 0.0,
    fees: float = 0.0,
    hours: float = 0.0,
    hourly_value: float = 0.0,
    risk_haircut_pct: float = 0.0,
) -> dict:
    """Net cash to you after payoff. Include time and a risk haircut (scams, no-shows, disputes) for private sales."""
    gross = price + tax_credit
    costs = listing_cost + prep_cost + fees + hours * hourly_value + price * risk_haircut_pct / 100
    return {
        "channel": channel,
        "price": price,
        "tax_credit": tax_credit,
        "costs": costs,
        "net_after_payoff": gross - costs - payoff,
    }


# ----------------------------------------------------------------------------
# 4. BUYER MATH: LOANS, OTD, NEGATIVE EQUITY
# ----------------------------------------------------------------------------


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def loan_payment(principal: float, apr_pct: float, months: int) -> float:
    r = apr_pct / 100 / 12
    return principal / months if r == 0 else principal * r / (1 - (1 + r) ** -months)


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def amortization(principal: float, apr_pct: float, months: int) -> pd.DataFrame:
    pay, r, bal, rows = loan_payment(principal, apr_pct, months), apr_pct / 100 / 12, principal, []
    for m in range(1, months + 1):
        interest = bal * r
        bal = bal + interest - pay
        rows.append((m, pay, interest, pay - interest, max(bal, 0.0)))
    return pd.DataFrame(rows, columns=["month", "payment", "interest", "principal", "balance"])


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def otd_price(
    vehicle_price: float,
    doc_fee: float,
    addons: float,
    sales_tax_rate_pct: float,
    title_reg: float,
    trade_value: float = 0.0,
    state_trade_credit: bool = True,
    rebates: float = 0.0,
    destination_included: bool = True,
) -> dict:
    """Out-the-door price. Sales tax base varies by state (some tax doc fees/addons; some give trade-in credit;
    rebates may or may not reduce the taxable base): VERIFY with your state DOR/dealer. This uses a common simple form."""
    taxable = vehicle_price + doc_fee + addons - (trade_value if state_trade_credit else 0.0)
    tax = max(taxable, 0.0) * sales_tax_rate_pct / 100
    total = vehicle_price + doc_fee + addons + tax + title_reg - trade_value - rebates
    return {
        "vehicle": vehicle_price,
        "doc_fee": doc_fee,
        "addons": addons,
        "tax": tax,
        "title_reg": title_reg,
        "trade_credit": trade_value,
        "rebates": rebates,
        "out_the_door": total,
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def negative_equity_months(
    price: float, down: float, apr_pct: float, months: int, value_fn
) -> dict:
    """First month in which loan balance <= market value (positive equity), using value_fn(month)->value.
    Returns months underwater and the max shortfall. value_fn is YOUR depreciation model (placeholder-friendly)."""
    am = amortization(price - down, apr_pct, months)
    vals = np.array([value_fn(m) for m in am.month])
    gap = am.balance.values - vals
    under = gap > 0
    first_pos = next((int(m) for m, u in zip(am.month, under, strict=True) if not u), None)
    return {
        "months_underwater": int(under.sum()),
        "first_positive_equity_month": first_pos,
        "max_gap": float(gap.max()),
        "gap_at_month_12": float(gap[11]) if months >= 12 else None,
        "gap_at_month_36": float(gap[35]) if months >= 36 else None,
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def gap_needed(
    price: float, down: float, apr_pct: float, months: int, value_fn, horizon_months: int = 36
) -> float:
    """Worst-case shortfall over the first `horizon_months` (what GAP would cover in a total loss)."""
    am = amortization(price - down, apr_pct, months).head(horizon_months)
    vals = np.array([value_fn(m) for m in am.month])
    return float(max((am.balance.values - vals).max(), 0.0))


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def term_comparison(principal: float, apr_by_term: dict[int, float]) -> pd.DataFrame:
    rows = []
    for t, apr in apr_by_term.items():
        p = loan_payment(principal, apr, t)
        rows.append((t, apr, p, p * t - principal, p * t))
    return pd.DataFrame(rows, columns=["months", "apr", "payment", "total_interest", "total_paid"])


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def affordability_20_4_10(
    gross_monthly_income: float,
    apr_pct: float = 7.0,
    term_months: int = 48,
    down_pct: float = 20.0,
    insurance_monthly: float = 0.0,
    fuel_maint_monthly: float = 0.0,
) -> dict:
    """Heuristic ('20/4/10'): >=20% down, <=4-year loan, total transport costs <=10% of gross income. A guardrail,
    not a law. Returns the price ceiling that keeps TOTAL monthly transportation cost within 10% of income."""
    budget = 0.10 * gross_monthly_income - insurance_monthly - fuel_maint_monthly
    factor = loan_payment(1.0, apr_pct, term_months)
    loan_cap = max(budget, 0) / factor
    price_cap = loan_cap / (1 - down_pct / 100)
    return {
        "monthly_budget_for_payment": max(budget, 0),
        "max_loan": loan_cap,
        "max_price": price_cap,
    }


# ----------------------------------------------------------------------------
# 5. OWNERSHIP ECONOMICS
# ----------------------------------------------------------------------------


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def tco(
    price: float,
    years: float,
    miles_per_year: float,
    resale_value: float,
    apr_pct: float,
    down: float,
    loan_months: int,
    insurance_yr: float,
    fuel_cost_per_mile: float,
    maintenance_yr: float,
    registration_yr: float = 0.0,
    repairs_yr: float = 0.0,
    sales_tax_pct: float = 0.0,
    fees: float = 0.0,
) -> dict:
    """Total cost of ownership over the holding period (cash view; ignores opportunity cost of down payment).
    Interest = interest actually paid during the holding period."""
    principal = price * (1 + sales_tax_pct / 100) + fees - down
    am = amortization(principal, apr_pct, loan_months)
    months = int(round(years * 12))
    interest = float(am.head(months).interest.sum())
    dep = price - resale_value
    run = (
        insurance_yr + maintenance_yr + registration_yr + repairs_yr
    ) * years + fuel_cost_per_mile * miles_per_year * years
    total = dep + interest + run + price * sales_tax_pct / 100 + fees
    miles = miles_per_year * years
    return {
        "depreciation": dep,
        "interest": interest,
        "tax_fees": price * sales_tax_pct / 100 + fees,
        "running_costs": run,
        "total": total,
        "per_year": total / years,
        "per_mile": total / miles,
        "per_month": total / (years * 12),
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def lease_payment(
    msrp_or_cap_cost: float,
    residual_pct: float,
    term_months: int,
    money_factor: float,
    cap_cost_reduction: float = 0.0,
    acq_fee: float = 0.0,
    tax_rate_pct: float = 0.0,
) -> dict:
    """Monthly lease payment. Money factor x 2400 ~ APR. Residual% is of MSRP; negotiate the CAP COST like a purchase price.
    Tax treatment varies by state (monthly payment tax vs upfront)."""
    cap = msrp_or_cap_cost - cap_cost_reduction + acq_fee
    resid = msrp_or_cap_cost * residual_pct / 100
    dep_fee = (cap - resid) / term_months
    rent_fee = (cap + resid) * money_factor
    pre_tax = dep_fee + rent_fee
    return {
        "cap_cost": cap,
        "residual": resid,
        "depreciation_fee": dep_fee,
        "rent_charge": rent_fee,
        "equiv_apr_pct": money_factor * 2400,
        "monthly_pre_tax": pre_tax,
        "monthly_with_tax": pre_tax * (1 + tax_rate_pct / 100),
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def lease_vs_buy(
    price: float,
    residual_pct: float,
    term_months: int,
    money_factor: float,
    lease_down: float,
    buy_apr_pct: float,
    buy_down: float,
    buy_value_at_end: float,
    tax_rate_pct: float = 0.0,
    invest_return_pct: float = 0.0,
) -> dict:
    """Compare cash out over the lease term, treating buy-side resale value at term end as an asset.
    Lease: payments + down. Buy: payments + down - resale. Includes the OPPORTUNITY cost of down payments if invest_return>0."""
    lp = lease_payment(
        price, residual_pct, term_months, money_factor, lease_down, 0.0, tax_rate_pct
    )
    lease_cash = lp["monthly_with_tax"] * term_months + lease_down
    principal = price * (1 + tax_rate_pct / 100) - buy_down
    bp = loan_payment(principal, buy_apr_pct, term_months)
    bal = amortization(principal, buy_apr_pct, term_months).balance.iloc[-1]
    buy_cash = bp * term_months + buy_down
    yrs = term_months / 12

    def opp(amt: float) -> float:
        return amt * ((1 + invest_return_pct / 100) ** yrs - 1)

    buy_net = buy_cash - (buy_value_at_end - bal)  # payments + down - equity at end
    return {
        "lease_monthly": lp["monthly_with_tax"],
        "buy_monthly": bp,
        "lease_total_cash": lease_cash,
        "buy_total_cash": buy_cash,
        "buy_net_of_resale": buy_net,
        "lease_net_incl_opp": lease_cash + opp(lease_down),
        "buy_net_incl_opp": buy_net + opp(buy_down),
        "lease_equiv_apr_pct": lp["equiv_apr_pct"],
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def ev_vs_ice(
    miles_per_year: float,
    kwh_per_mile: float,
    price_per_kwh: float,
    home_charge_share: float,
    public_price_per_kwh: float,
    mpg: float,
    price_per_gallon: float,
) -> dict:
    ev_cost_mile = kwh_per_mile * (
        home_charge_share * price_per_kwh + (1 - home_charge_share) * public_price_per_kwh
    )
    ice_cost_mile = price_per_gallon / mpg
    return {
        "ev_per_mile": ev_cost_mile,
        "ice_per_mile": ice_cost_mile,
        "annual_ev": ev_cost_mile * miles_per_year,
        "annual_ice": ice_cost_mile * miles_per_year,
        "annual_saving_ev": (ice_cost_mile - ev_cost_mile) * miles_per_year,
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def repair_or_replace(
    vehicle_value: float,
    repair_cost: float,
    expected_extra_years: float,
    replacement_monthly_cost: float,
    current_monthly_cost: float = 0.0,
    expected_other_repairs_yr: float = 0.0,
) -> dict:
    """Compare keeping (repair + other expected repairs + current costs) vs replacing (monthly cost incl. depreciation/interest).
    Rule of thumb: repair if cost < ~half of value AND remaining life > ~1 year AND repair addresses a root cause."""
    keep_total = (
        repair_cost
        + expected_other_repairs_yr * expected_extra_years
        + current_monthly_cost * 12 * expected_extra_years
    )
    replace_total = replacement_monthly_cost * 12 * expected_extra_years
    return {
        "keep_total": keep_total,
        "replace_total": replace_total,
        "repair_to_value_pct": 100 * repair_cost / vehicle_value,
        "decision_hint": "keep"
        if keep_total < replace_total and repair_cost < 0.5 * vehicle_value
        else "replace/consider",
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def rebate_vs_low_apr(
    price: float,
    rebate: float,
    months: int,
    market_apr_pct: float,
    promo_apr_pct: float = 0.0,
    down: float = 0.0,
) -> dict:
    """Manufacturer offers EITHER a cash rebate (finance at your market APR) OR a promotional APR (usually 0-3.9%,
    no rebate). Compare TOTAL cash paid over the term (down + payments). Taking the low APR is not automatically 'free'."""
    p_rebate = loan_payment(price - rebate - down, market_apr_pct, months)
    p_promo = loan_payment(price - down, promo_apr_pct, months)
    tot_rebate = down + p_rebate * months
    tot_promo = down + p_promo * months
    return {
        "rebate_payment": p_rebate,
        "promo_payment": p_promo,
        "rebate_total": tot_rebate,
        "promo_total": tot_promo,
        "better": "promo APR" if tot_promo < tot_rebate else "cash rebate",
        "saving": abs(tot_rebate - tot_promo),
    }


if __name__ == "__main__":
    print("carval toolkit loaded. Run test_carval.py for the worked example.")
