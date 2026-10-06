#!/usr/bin/env python3
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""
bizval.py - dependency-light (numpy + pandas) toolkit for valuing, buying and selling companies and
analysing non-profits. NOT advice; every default is a PLACEHOLDER to replace with evidence.

 Earnings ........ sde(), adjusted_ebitda(), weighted_average_earnings()
 Multiples ....... comps_stats(), fit_multiple_model(), predict_multiple(), ev_to_equity()
 Income approach . capm_cost_of_equity(), wacc(), unlever_beta(), relever_beta(), dcf(), dcf_sensitivity(),
                   capitalized_earnings(), implied_discount_rate()
 Discounts ....... apply_discounts(), control_premium_from_minority_discount()
 Deal structure .. deal_pv(), loan_payment(), dscr(), max_price_for_dscr(), sba_sources_uses(), lbo()
 Tax ............. asset_vs_stock(), qsbs_exclusion()
 Startups ........ post_money_round(), safe_post_money_conversion(), venture_method()
 Non-profits ..... np_ratios(), np_adjusted_net_assets(), hhi(), sroi(), np_runway()
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

# =====================================================================================================
# 1. EARNINGS NORMALIZATION
# =====================================================================================================


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def sde(
    net_income: float,
    owner_comp: float,
    interest: float = 0.0,
    taxes: float = 0.0,
    depreciation_amort: float = 0.0,
    one_time_expenses: float = 0.0,
    personal_expenses: float = 0.0,
    other_addbacks: float = 0.0,
    one_time_income: float = 0.0,
) -> float:
    """Seller's Discretionary Earnings = pre-tax, pre-interest, pre-D&A earnings to ONE full-time owner-operator.
    Includes owner's total compensation (salary + benefits + payroll taxes on it). Subtract non-recurring income."""
    return (
        net_income
        + owner_comp
        + interest
        + taxes
        + depreciation_amort
        + one_time_expenses
        + personal_expenses
        + other_addbacks
        - one_time_income
    )


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def adjusted_ebitda(sde_value: float, replacement_manager_cost: float) -> float:
    """EBITDA ~ SDE minus a market-rate replacement for the owner's work (fully loaded)."""
    return sde_value - replacement_manager_cost


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def quality_weighted_addbacks(addbacks: list[tuple[float, float]]) -> float:
    """Quality-of-earnings style: each add-back is (amount, support_probability 0..1). Returns expected accepted amount.
    Buyers accept documented, one-time, non-operating add-backs; they haircut 'estimates' and 'owner says'."""
    return sum(a * p for a, p in addbacks)


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def weighted_average_earnings(values: list[float], weights: list[float] | None = None) -> float:
    w = np.array(weights if weights is not None else np.arange(1, len(values) + 1), dtype=float)
    return float(np.dot(values, w) / w.sum())


# =====================================================================================================
# 2. MARKET APPROACH
# =====================================================================================================


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def comps_stats(multiples: pd.Series) -> dict:
    m = multiples.dropna().astype(float)
    return {
        "n": int(m.size),
        "mean": float(m.mean()),
        "median": float(m.median()),
        "q1": float(m.quantile(0.25)),
        "q3": float(m.quantile(0.75)),
        "harmonic_mean": float(m.size / (1.0 / m).sum()),
        "min": float(m.min()),
        "max": float(m.max()),
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def fit_multiple_model(df: pd.DataFrame) -> dict:
    """ln(EV/EBITDA) = b0 + b1 ln(EBITDA) + b2 growth + b3 margin + b4 recurring + b5 top_customer_share.
    Columns: ev, ebitda, growth(0.10=10%), margin, recurring(0..1 share), top_customer (0..1)."""
    d = df.copy()
    y = np.log(d.ev / d.ebitda)
    X = np.column_stack(
        [np.ones(len(d)), np.log(d.ebitda), d.growth, d.margin, d.recurring, d.top_customer]
    )
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    sd = float(np.sqrt((res**2).sum() / (len(d) - X.shape[1])))
    r2 = float(1 - (res**2).sum() / ((y - y.mean()) ** 2).sum())
    return {
        "beta": dict(
            zip(
                ["const", "ln_ebitda", "growth", "margin", "recurring", "top_customer"],
                beta,
                strict=True,
            )
        ),
        "resid_sd": sd,
        "r2": r2,
        "n": len(d),
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def predict_multiple(
    model: dict, ebitda: float, growth: float, margin: float, recurring: float, top_customer: float
) -> dict:
    b = model["beta"]
    x = (
        b["const"]
        + b["ln_ebitda"] * math.log(ebitda)
        + b["growth"] * growth
        + b["margin"] * margin
        + b["recurring"] * recurring
        + b["top_customer"] * top_customer
    )
    m = math.exp(x)
    sd = model["resid_sd"]
    return {
        "multiple": m,
        "p10": m * math.exp(-1.2816 * sd),
        "p90": m * math.exp(1.2816 * sd),
        "ev": m * ebitda,
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def ev_to_equity(
    ev: float,
    debt: float,
    cash: float,
    debt_like: float = 0.0,
    nwc_shortfall: float = 0.0,
    minority_interests: float = 0.0,
) -> dict:
    """Cash-free, debt-free price -> equity proceeds. Debt-like: deferred revenue (if cash already collected), unpaid taxes,
    accrued bonuses, capital leases, deferred capex, customer deposits, litigation reserves, earnout liabilities."""
    eq = ev - debt - debt_like - nwc_shortfall - minority_interests + cash
    return {"ev": ev, "equity_value": eq, "net_debt_and_adjustments": ev - eq}


# =====================================================================================================
# 3. INCOME APPROACH
# =====================================================================================================


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def capm_cost_of_equity(
    rf: float, erp: float, beta: float, size_premium: float = 0.0, company_specific: float = 0.0
) -> float:
    return rf + beta * erp + size_premium + company_specific


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def unlever_beta(levered_beta: float, debt_to_equity: float, tax_rate: float) -> float:
    return levered_beta / (1 + (1 - tax_rate) * debt_to_equity)


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def relever_beta(unlevered_beta: float, debt_to_equity: float, tax_rate: float) -> float:
    return unlevered_beta * (1 + (1 - tax_rate) * debt_to_equity)


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def wacc(
    cost_equity: float, cost_debt_pre_tax: float, debt_weight: float, tax_rate: float
) -> float:
    return (1 - debt_weight) * cost_equity + debt_weight * cost_debt_pre_tax * (1 - tax_rate)


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def fcff(ebitda: float, da: float, capex: float, delta_nwc: float, tax_rate: float) -> float:
    ebit = ebitda - da
    return ebit * (1 - tax_rate) + da - capex - delta_nwc


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def dcf(
    cash_flows: list[float],
    rate: float,
    terminal_growth: float | None = None,
    exit_multiple: float | None = None,
    terminal_metric: float | None = None,
    mid_year: bool = False,
) -> dict:
    """PV of explicit cash flows + terminal value. Gordon: TV = CF_n(1+g)/(r-g).  Exit: TV = multiple * metric_n.
    Returns EV, TV share and implied exit multiple / implied perpetual growth for cross-checking."""
    n = len(cash_flows)
    shift = 0.5 if mid_year else 0.0
    pv_cf = sum(cf / (1 + rate) ** (t + 1 - shift) for t, cf in enumerate(cash_flows))
    if terminal_growth is not None:
        if rate <= terminal_growth:
            raise ValueError("rate must exceed terminal growth")
        tv = cash_flows[-1] * (1 + terminal_growth) / (rate - terminal_growth)
        tv_pv = tv / (1 + rate) ** (n - shift if mid_year else n)
    else:
        tv = exit_multiple * terminal_metric
        tv_pv = tv / (1 + rate) ** n
    ev = pv_cf + tv_pv
    out = {
        "ev": ev,
        "pv_explicit": pv_cf,
        "pv_terminal": tv_pv,
        "tv_share": tv_pv / ev,
        "terminal_value": tv,
    }
    if terminal_metric:
        out["implied_exit_multiple"] = tv / terminal_metric
    if exit_multiple is not None:
        # growth g solving TV = CF(1+g)/(r-g)  ->  g = (TV*r - CF)/(TV + CF)
        out["implied_perpetual_growth"] = (tv * rate - cash_flows[-1]) / (tv + cash_flows[-1])
    return out


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def dcf_sensitivity(
    cash_flows: list[float], rates: list[float], growths: list[float]
) -> pd.DataFrame:
    return pd.DataFrame(
        [[dcf(cash_flows, r, terminal_growth=g)["ev"] for g in growths] for r in rates],
        index=[f"r={r:.1%}" for r in rates],
        columns=[f"g={g:.1%}" for g in growths],
    )


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def capitalized_earnings(normalized_cash_flow: float, discount_rate: float, growth: float) -> float:
    """Single-period capitalization: CF1/(r-g); CF1 = normalized_cash_flow*(1+g)."""
    return normalized_cash_flow * (1 + growth) / (discount_rate - growth)


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def implied_discount_rate(price: float, next_year_cash_flow: float, growth: float) -> float:
    """What return is a buyer actually underwriting? r = CF1/P + g."""
    return next_year_cash_flow / price + growth


# =====================================================================================================
# 4. DISCOUNTS AND PREMIUMS
# =====================================================================================================


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def apply_discounts(
    value: float,
    minority_pct: float = 0.0,
    dlom_pct: float = 0.0,
    key_person_pct: float = 0.0,
    concentration_pct: float = 0.0,
) -> dict:
    """Sequential (multiplicative) discounts to reach a lower 'level of value'. Each % is a judgment to be SUPPORTED
    (restricted-stock/pre-IPO studies for DLOM; transaction data; fact patterns). Do not stack reflexively."""
    v = value
    steps = {}
    for name, pct in [
        ("minority/lack of control", minority_pct),
        ("marketability (DLOM)", dlom_pct),
        ("key person", key_person_pct),
        ("customer concentration", concentration_pct),
    ]:
        if pct:
            v2 = v * (1 - pct / 100)
            steps[name] = v2 - v
            v = v2
    return {"value": v, "combined_discount_pct": 100 * (1 - v / value), "steps": steps}


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def control_premium_from_minority_discount(minority_discount: float) -> float:
    """Control premium = 1/(1 - MD) - 1."""
    return 1.0 / (1.0 - minority_discount) - 1.0


# =====================================================================================================
# 5. DEAL STRUCTURE AND FINANCING
# =====================================================================================================


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def loan_payment(principal: float, apr: float, years: float) -> float:
    r, n = apr / 12, int(round(years * 12))
    return principal / n if r == 0 else principal * r / (1 - (1 + r) ** -n)


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def dscr(cash_flow_for_debt_service: float, annual_debt_service: float) -> float:
    return cash_flow_for_debt_service / annual_debt_service


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def max_price_for_dscr(
    cash_flow_for_debt_service: float,
    min_dscr: float,
    apr: float,
    years: float,
    equity_pct: float = 0.10,
    seller_standby_pct: float = 0.0,
    other_costs_pct: float = 0.03,
) -> dict:
    """Largest purchase price an acquisition loan can support. Max annual debt service = CF/min_dscr.
    Loan funds (1 - equity_pct) of total project cost (price*(1+other_costs)); a full-standby seller note counts as equity
    but isn't serviced during the loan. (SBA: equity >=10% of total project cost; 7(a) <= 10-year amortization for change of ownership.)"""
    max_ds = cash_flow_for_debt_service / min_dscr
    pay_per_dollar = loan_payment(1.0, apr, years) * 12
    max_loan = max_ds / pay_per_dollar
    project_cost = max_loan / (1 - equity_pct)
    price = project_cost / (1 + other_costs_pct)
    return {
        "max_annual_debt_service": max_ds,
        "max_loan": max_loan,
        "total_project_cost": project_cost,
        "max_price": price,
        "equity_needed": project_cost * equity_pct,
        "seller_standby_allowed_max": project_cost * equity_pct * 0.5,
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def sba_sources_uses(
    price: float,
    fees_and_costs: float = 0.0,
    working_capital: float = 0.0,
    equity_pct: float = 0.10,
    seller_standby_share_of_equity: float = 0.5,
) -> dict:
    """SOP 50 10 8 (June 1 2025): >=10% equity injection of total project cost for a complete change of ownership;
    a seller note can count only if on FULL STANDBY for the life of the loan and <= 50% of the required injection (8.1, effective
    Oct 1 2026, also caps standby debt + outside investor equity combined at 50%). VERIFY current SOP before relying."""
    total = price + fees_and_costs + working_capital
    equity_req = total * equity_pct
    seller_standby = min(equity_req * seller_standby_share_of_equity, equity_req * 0.5)
    buyer_cash = equity_req - seller_standby
    loan = total - equity_req
    return {
        "total_project_cost": total,
        "equity_required": equity_req,
        "buyer_cash": buyer_cash,
        "seller_standby_note": seller_standby,
        "sba_loan": loan,
        "loan_pct": loan / total,
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def deal_pv(
    cash_at_close: float,
    seller_note: float = 0.0,
    note_rate: float = 0.0,
    note_years: float = 0.0,
    earnout_max: float = 0.0,
    earnout_prob: float = 0.0,
    earnout_year: float = 0.0,
    rollover_value: float = 0.0,
    rollover_haircut: float = 0.0,
    discount_rate: float = 0.12,
    escrow: float = 0.0,
    escrow_release_prob: float = 0.85,
    escrow_years: float = 1.5,
) -> dict:
    """Headline price vs. present value to the SELLER (risk-adjusted). Seller note valued at the seller's required return
    (discount_rate), not at the note coupon; earnouts probability-weighted; rollover haircut for illiquidity/minority."""
    note_pv = 0.0
    if seller_note:
        n = int(round(note_years * 12))
        pay = loan_payment(seller_note, note_rate, note_years)
        mr = (1 + discount_rate) ** (1 / 12) - 1
        note_pv = sum(pay / (1 + mr) ** m for m in range(1, n + 1))
    earn_pv = (
        earnout_max * earnout_prob / (1 + discount_rate) ** earnout_year if earnout_max else 0.0
    )
    esc_pv = escrow * escrow_release_prob / (1 + discount_rate) ** escrow_years if escrow else 0.0
    roll_pv = rollover_value * (1 - rollover_haircut)
    headline = cash_at_close + seller_note + earnout_max + rollover_value + escrow
    pv = cash_at_close + note_pv + earn_pv + roll_pv + esc_pv
    return {
        "headline": headline,
        "pv": pv,
        "pv_pct_of_headline": pv / headline,
        "cash_at_close_pct": cash_at_close / headline,
        "note_pv": note_pv,
        "earnout_pv": earn_pv,
        "rollover_pv": roll_pv,
        "escrow_pv": esc_pv,
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def irr(cash_flows: list[float]) -> float:
    lo, hi = -0.99, 10.0

    def f(r: float) -> float:
        return sum(cf / (1 + r) ** t for t, cf in enumerate(cash_flows))

    if f(lo) * f(hi) > 0:
        return float("nan")
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def lbo(
    entry_ebitda: float,
    entry_multiple: float,
    debt_multiple: float,
    interest_rate: float,
    growth: float,
    years: int,
    exit_multiple: float,
    tax_rate: float = 0.25,
    capex_pct_ebitda: float = 0.15,
    nwc_pct_ebitda_growth: float = 0.10,
    fees_pct: float = 0.03,
    sweep: float = 1.0,
) -> dict:
    """Simplified LBO: EBITDA grows at `growth`; FCF = (EBITDA - capex) - taxes on (EBITDA - D&A(=capex) - interest) - dNWC - interest;
    swept to debt. Returns sponsor MOIC and IRR."""
    ev = entry_ebitda * entry_multiple
    debt = entry_ebitda * debt_multiple
    equity0 = ev * (1 + fees_pct) - debt
    e = entry_ebitda
    for _ in range(years):
        e_new = e * (1 + growth)
        interest = debt * interest_rate
        capex = e_new * capex_pct_ebitda
        taxes = max((e_new - capex - interest) * tax_rate, 0.0)
        dnwc = (e_new - e) * nwc_pct_ebitda_growth * 3
        fcf = e_new - capex - taxes - dnwc - interest
        debt = max(debt - max(fcf, 0.0) * sweep, 0.0)
        e = e_new
    exit_ev = e * exit_multiple
    equity_exit = exit_ev - debt
    moic = equity_exit / equity0
    return {
        "entry_ev": ev,
        "equity_in": equity0,
        "exit_ev": exit_ev,
        "debt_at_exit": debt,
        "equity_out": equity_exit,
        "moic": moic,
        "irr": moic ** (1 / years) - 1 if moic > 0 else float("nan"),
    }


# =====================================================================================================
# 6. TAX: ASSET vs STOCK, QSBS
# =====================================================================================================


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def asset_vs_stock(
    price: float,
    stock_basis: float,
    ordinary_recapture: float,
    inventory_ar_ordinary: float,
    ltcg_rate: float = 0.20,
    niit: float = 0.038,
    ordinary_rate: float = 0.37,
    state_rate: float = 0.05,
    buyer_tax_rate: float = 0.25,
    buyer_discount_rate: float = 0.12,
    amort_years: int = 15,
    asset_basis_total: float | None = None,
) -> dict:
    """Stylized comparison for a PASS-THROUGH or S-corp seller (C-corp double-tax and 338(h)(10)/F-reorg structures differ).
    Stock sale: all gain at LTCG+NIIT(+state). Asset sale: ordinary income on recapture and inventory/AR, remainder capital gain.
    Buyer's step-up: goodwill/intangibles amortised over 15 years -> PV of tax shield. 100% bonus depreciation (permanent for property
    acquired after Jan 19 2025) can make the buyer's equipment step-up far more valuable. NOT tax advice."""
    cg_rate = ltcg_rate + niit + state_rate
    ord_rate = ordinary_rate + niit + state_rate
    stock_tax = (price - stock_basis) * cg_rate
    asset_basis_total = stock_basis if asset_basis_total is None else asset_basis_total
    ordinary_amt = ordinary_recapture + inventory_ar_ordinary
    cap_gain = max(price - asset_basis_total - ordinary_amt, 0.0)
    asset_tax = ordinary_amt * ord_rate + cap_gain * cg_rate
    stepup = max(price - asset_basis_total, 0.0)
    shield = sum(
        stepup / amort_years * buyer_tax_rate / (1 + buyer_discount_rate) ** t
        for t in range(1, amort_years + 1)
    )
    seller_penalty = asset_tax - stock_tax
    return {
        "stock_sale_tax": stock_tax,
        "asset_sale_tax": asset_tax,
        "seller_extra_tax_in_asset_deal": seller_penalty,
        "buyer_stepup_pv": shield,
        "gross_up_needed_pct_of_price": 100 * seller_penalty / price,
        "net_to_seller_stock": price - stock_tax,
        "net_to_seller_asset": price - asset_tax,
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def qsbs_exclusion(
    gain: float, holding_years: float, issued_after_july4_2025: bool, basis: float = 0.0
) -> dict:
    """Section 1202. Post-July-4-2025 stock: 50% at 3y, 75% at 4y, 100% at 5y; cap greater of $15M or 10x basis; the non-excluded
    portion of a 3/4-year hold is taxed at up to 28% (+3.8% NIIT). Pre-OBBBA stock: 100% only at 5y; cap greater of $10M or 10x basis.
    Eligibility (C-corp, <= $75M/$50M gross assets at issuance, active business, original issuance) must be verified by counsel."""
    if issued_after_july4_2025:
        pct = (
            1.0
            if holding_years >= 5
            else 0.75
            if holding_years >= 4
            else 0.50
            if holding_years >= 3
            else 0.0
        )
        cap = max(15_000_000, 10 * basis)
    else:
        pct = 1.0 if holding_years >= 5 else 0.0
        cap = max(10_000_000, 10 * basis)
    excludable = min(gain * pct, cap)
    taxable = gain - excludable
    rate_taxable = (
        0.28 if (issued_after_july4_2025 and 3 <= holding_years < 5 and pct > 0) else 0.20
    )
    tax = taxable * (rate_taxable + 0.038)
    return {
        "exclusion_pct": pct,
        "cap": cap,
        "excluded_gain": excludable,
        "taxable_gain": taxable,
        "federal_tax": tax,
        "effective_rate": tax / gain if gain else 0.0,
    }


# =====================================================================================================
# 7. STARTUPS
# =====================================================================================================


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def post_money_round(
    pre_money: float, raise_amt: float, option_pool_topup_pct_post: float = 0.0
) -> dict:
    post = pre_money + raise_amt
    investor_pct = raise_amt / post
    return {
        "post_money": post,
        "investor_pct": investor_pct,
        "existing_holders_pct": 1 - investor_pct - option_pool_topup_pct_post,
        "effective_pre_money_after_pool": pre_money - option_pool_topup_pct_post * post,
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def safe_post_money_conversion(
    investment: float,
    post_money_cap: float,
    round_pre_money: float,
    round_price_discount: float = 0.0,
    pre_round_fully_diluted_shares: float = 10_000_000,
    new_money: float = 0.0,
) -> dict:
    """Post-money SAFE converts at min(cap price, discounted price). Cap ownership = investment/post_money_cap (before new money)."""
    cap_pct = investment / post_money_cap
    # price per share at the priced round (pre-money / pre-round fully diluted incl. SAFE conversions simplified)
    round_price = round_pre_money / pre_round_fully_diluted_shares
    cap_price = round_price * min(1.0, post_money_cap / max(round_pre_money, 1.0))
    disc_price = round_price * (1 - round_price_discount)
    price = min(cap_price, disc_price) if round_price_discount else cap_price
    return {
        "cap_ownership_pct_before_new_money": cap_pct,
        "conversion_price": price,
        "round_price": round_price,
        "shares": investment / price,
        "converts_at": "cap" if price == cap_price else "discount",
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def venture_method(
    exit_value: float,
    years: float,
    target_multiple: float,
    expected_dilution: float,
    raise_amt: float = 0.0,
) -> dict:
    """Required post-money today for an investor to hit `target_multiple` (MOIC) given exit value and later dilution.
    post_money = exit_value * (1 - dilution) / target_multiple ; pre = post - raise."""
    post = exit_value * (1 - expected_dilution) / target_multiple
    return {
        "post_money": post,
        "pre_money": post - raise_amt,
        "target_irr": target_multiple ** (1 / years) - 1,
    }


# =====================================================================================================
# 8. NON-PROFIT ANALYSIS
# =====================================================================================================


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def hhi(shares: list[float]) -> float:
    s = np.array(shares, dtype=float)
    s = s / s.sum()
    return float((s**2).sum())


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def np_ratios(
    total_revenue: float,
    government_grants: float,
    contributions: float,
    program_fees: float,
    other_revenue: float,
    total_expenses: float,
    program_expenses: float,
    fundraising_expenses: float,
    mgmt_general_expenses: float,
    cash_and_equivalents: float,
    investments_liquid: float,
    receivables: float,
    current_liabilities: float,
    total_assets: float,
    total_liabilities: float,
    net_assets_without_restrictions: float,
    net_ppe: float,
    debt: float = 0.0,
    contributions_raised_for_fundraising_ratio: float | None = None,
) -> dict:
    """Core Form-990/audit ratios with the *interpretation traps* in the SKILL (read with trend, reserves and restrictions)."""
    monthly_exp = total_expenses / 12
    luna = (
        net_assets_without_restrictions - net_ppe - 0.0
    )  # liquid unrestricted net assets (simplified; also subtract board-designated illiquid items)
    cr = (
        contributions
        if contributions_raised_for_fundraising_ratio is None
        else contributions_raised_for_fundraising_ratio
    )
    rev_mix = [government_grants, contributions, program_fees, other_revenue]
    return {
        "surplus_margin": (total_revenue - total_expenses) / total_revenue,
        "program_expense_ratio": program_expenses / total_expenses,
        "fundraising_cost_per_dollar": fundraising_expenses / cr if cr else float("nan"),
        "months_of_cash": cash_and_equivalents / monthly_exp,
        "months_of_liquid_assets": (cash_and_equivalents + investments_liquid) / monthly_exp,
        "luna": luna,
        "months_of_luna": luna / monthly_exp,
        "current_ratio": (cash_and_equivalents + investments_liquid + receivables)
        / current_liabilities,
        "debt_to_assets": total_liabilities / total_assets,
        "debt_to_net_assets_unrestricted": debt / net_assets_without_restrictions
        if net_assets_without_restrictions
        else float("nan"),
        "top_source_share": max(rev_mix) / total_revenue,
        "government_share": government_grants / total_revenue,
        "revenue_hhi": hhi(rev_mix),
        "contribution_dependence": contributions / total_revenue,
    }


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def np_adjusted_net_assets(
    total_assets_book: float,
    liabilities_book: float,
    fair_value_adjustments: float,
    donor_restricted_perpetual: float = 0.0,
    restricted_time_purpose: float = 0.0,
    contingent_liabilities: float = 0.0,
    deferred_maintenance: float = 0.0,
) -> dict:
    """What a counterparty can actually rely on: net assets at fair value, less amounts that cannot move to the successor
    (permanently restricted endowment; purpose-restricted gifts must follow their restrictions), less contingent liabilities and
    deferred maintenance. This is a FLOOR/REFERENCE for transactions, not a 'price'."""
    fv_net = (
        total_assets_book
        + fair_value_adjustments
        - liabilities_book
        - contingent_liabilities
        - deferred_maintenance
    )
    unencumbered = fv_net - donor_restricted_perpetual - restricted_time_purpose
    return {"fair_value_net_assets": fv_net, "unencumbered_net_assets": unencumbered}


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def sroi(
    outcomes: list[dict], investment: float, discount_rate: float = 0.035, horizon_years: int = 5
) -> dict:
    """Social return on investment. Each outcome: {'quantity': n, 'proxy_value': $ per unit per year, 'deadweight': 0..1,
    'attribution': 0..1 (share of change due to others, subtracted), 'displacement': 0..1, 'drop_off': 0..1 per year, 'years': k}.
    Value = quantity*proxy*(1-deadweight)*(1-attribution)*(1-displacement), decayed by drop_off, discounted.
    SROI = PV(value)/investment. Proxies are JUDGMENTS: report ranges and sensitivities."""
    pv = 0.0
    for o in outcomes:
        base = (
            o["quantity"]
            * o["proxy_value"]
            * (1 - o.get("deadweight", 0))
            * (1 - o.get("attribution", 0))
            * (1 - o.get("displacement", 0))
        )
        for t in range(1, min(o.get("years", 1), horizon_years) + 1):
            pv += base * (1 - o.get("drop_off", 0)) ** (t - 1) / (1 + discount_rate) ** t
    return {"pv_social_value": pv, "investment": investment, "sroi_ratio": pv / investment}


# Module-level by design (ADR-0016): a standalone toolkit its skills cite function by name.
def np_runway(
    cash: float,
    monthly_expenses: float,
    monthly_recurring_revenue: float,
    receivables_30_60: float = 0.0,
    pending_grants: list[tuple[float, float, int]] | None = None,
    months: int = 12,
) -> pd.DataFrame:
    """Month-by-month cash with probability-weighted grants [(amount, probability, month_received)]."""
    rows, bal = [], cash
    pg = pending_grants or []
    for m in range(1, months + 1):
        inflow = monthly_recurring_revenue + (receivables_30_60 if m == 2 else 0.0)
        inflow += sum(a * p for a, p, mo in pg if mo == m)
        bal += inflow - monthly_expenses
        rows.append((m, inflow, monthly_expenses, bal))
    return pd.DataFrame(rows, columns=["month", "inflow", "outflow", "cash"])


if __name__ == "__main__":
    print("bizval toolkit loaded. Run test_bizval.py for the verified worked examples.")
