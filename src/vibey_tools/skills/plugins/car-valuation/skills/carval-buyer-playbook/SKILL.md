---
name: carval-buyer-playbook
description: "Use when buying a car (new, used, CPO, online retailer or private party): budgeting from the total monthly cost (the 20/4/10 guardrail and its limits), financing (pre-approval, APR, loan terms, negative equity timelines, spot-delivery/yo-yo financing), new vs used vs CPO, shortlisting by reliability and total cost of ownership, reading listings and red flags, the three-number approach (market value, payment ceiling, walk-away), out-the-door price negotiation by email, dealer fees and add-ons, F&I products (extended warranty, GAP, protection packages), the step-by-step private-party purchase, and decision rules for EV vs gas, keep vs replace and rolling negative equity."
---

# Car Valuation and Market Research: The Buyer Playbook

> **Part 4 of 7** of the *Car Valuation and Market Research* reference (plugin `car-valuation`), covering §16–§20. Sibling skills: `carval-concepts-methods-and-market-structure` (§0–§4), `carval-market-analysis-and-timing` (§5–§9), `carval-valuing-a-specific-vehicle` (§10–§15), `carval-seller-playbook` (§21–§25), `carval-diligence-risk-and-ownership-economics` (§26–§30), `carval-reference` (§31–§35). Code: `scripts/carval.py` (`loan_payment`, `term_comparison`, `otd_price`, `negative_equity_months`, `gap_needed`, `affordability_20_4_10`, `tco`, `ev_vs_ice`, `repair_or_replace`).
>
> **Currency:** Procedures are stable; rates, fees and market numbers are **October 2026**. The APRs used in examples are **illustrative placeholders**: use your own quotes.

> **⚠️ Scope.** Educational; not lending, legal or insurance advice. State sales-tax, fee and title rules vary; verify with your DMV/dealer.

> **The three ideas:**
> 1. **⚠️ Negotiate the out-the-door (OTD) price, not the monthly payment.** Payments can be made to look good by stretching the term (84 months at 8.5% costs **$10,403 in interest on $31,500 vs $4,357** over 48 months at 6.5%) (§16, §18).
> 2. **⚠️ Decide three numbers before you step on a lot or answer an ad:** the market-value range (§15), your payment ceiling, and your walk-away OTD price. Don't revise the walk-away upward during the negotiation (§18).
> 3. **⚠️ Separate the four deals:** the car's price, your trade-in, the financing and the add-ons. Dealers can hide margin by shifting money among them (§18, §19).

---

## §16. Define the Decision: Budget, Financing and Total Cost

### 16.1 Budget from total monthly cost
- **Total transportation cost** = payment + insurance + fuel/energy + maintenance + registration/taxes + parking/tolls. **Budget on this total.**
- **The "20/4/10" guardrail** (≥20% down, loan ≤4 years, *total* transportation ≤10% of gross income) is a *conservative heuristic, not a rule.* The toolkit's `affordability_20_4_10()` shows how binding it is: at **$7,000/month gross income**, with $180 insurance and $250 fuel/maintenance, the payment budget is only **$270/month**, i.e., a **~$14,100 car** with 20% down at 7% over 48 months. Many buyers exceed it; **use it to see how far you are stretching**, not as a pass/fail test.
- **Reality check:** the average new-car loan is **$43,610 at $765/month over 69.5 months**; the average used loan is **$27,852 at $542/month over 67.9 months** (Experian Q2 2026, via a secondary summary). Buyers carrying **negative equity into a new loan average $944/month**.
- **Keep ≥3 months of expenses** as reserves after paying down/closing; avoid financing taxes, fees and add-ons.

### 16.2 Financing
| Step | What to do | Why |
|---|---|---|
| **Check your credit** | Pull reports from the three bureaus; fix errors | APR tier depends on score |
| **Get pre-approved** | 2–3 lenders, including a credit union, within a short window (rate-shopping inquiries for the same loan type are often grouped; verify the scoring model's window, commonly ~14–45 days) | You get a benchmark APR; the dealer must beat it |
| **Compare** | APR (not payment), term, fees, prepayment penalty, GAP/credit-insurance add-ons | Total cost |
| **At the dealer** | Share your pre-approval only *after* the price is agreed; ask if the dealer can beat it | Dealers may add an interest-rate markup on indirect loans |
| **Read the contract** | Retail installment contract: amount financed, APR, finance charge, total of payments, itemized add-ons | Numbers must match what you agreed |

**Term comparison (illustrative APRs; $31,500 financed):**
| Term | APR | Payment | Total interest | Total paid |
|---|---|---|---|---|
| 48 mo | 6.5% | $747 | $4,357 | $35,857 |
| 60 mo | 6.9% | $622 | $5,835 | $37,335 |
| 72 mo | 7.5% | $545 | $7,714 | $39,214 |
| 84 mo | 8.5% | $499 | $10,403 | $41,903 |
**Longer terms = lower payment, higher APR (often), far more interest, and much longer negative equity.**

**Negative-equity timeline (verified in the toolkit; $31,500 car + ~$1,900 tax/fees rolled in, $0 down, model retention curve):**
| Loan | Months underwater | Max gap | Gap at month 12 |
|---|---|---|---|
| 48 mo @ 6.5% | **11** | $2,616 | ≈ $0 (equity positive) |
| 72 mo @ 7.5% | **25** | $2,889 | $2,848 |
| 84 mo @ 8.5% | **36** | $3,780 | $3,780 |
**GAP coverage** is needed when you owe more than the car is worth (low down payment, long term, high-depreciation model); it covers the shortfall in a total loss. **Buy it from your insurer or credit union if possible** (usually cheaper than a dealer's), and **cancel/refund it when you're no longer underwater.**

### 16.3 New vs used vs CPO
| Option | Pros | Cons | Fits when |
|---|---|---|---|
| **New** | Warranty, latest tech, incentives/low APR promos | Steepest depreciation (first-year drop often 15–20%); higher insurance | You'll keep it 8+ years; promos beat used financing |
| **Used (2–5 yr)** | Prior owner absorbed the steepest drop; good remaining life | No/limited warranty; unknown history | Most buyers; get a PPI |
| **CPO (manufacturer-certified)** | Inspection + extended warranty | Premium price (placeholder ~$1,500); rules vary by brand | You value warranty and low hassle |
| **Dealer-"certified"** | Brand-neutral labels | **Not the same as CPO**: may be a dealer-only warranty | Verify exactly what it covers |
| **Old/cheap (8+ yr)** | Lowest depreciation, cheap insurance | Repairs; reliability needs proof | Reliable models with records; keep a repair fund |
| **EV** | Low running costs; federal credit **gone** after Sept 30, 2025 | Charging logistics; battery health uncertainty | Home charging; check state incentives |
**New-vehicle context (Aug 2026):** ATP **$50,089**; incentives 6.5% of ATP; used average sale **$27,239**. The gap between new and used has narrowed in some segments, so compare *total cost to own* (§28).

---

## §17. Search and Shortlist

### 17.1 Criteria
Write **needs (hard), wants (priced), dealbreakers (hard)**: seating/cargo, drivetrain, towing, safety features, range (EV), fuel type, reliability, insurance cost, **availability of service/parts in your area.**

### 17.2 Research sources
- **Reliability/safety:** Consumer Reports, J.D. Power dependability, **IIHS and NHTSA** ratings, **NHTSA recalls and TSBs by VIN**; owner forums for model-specific issues (engine, transmission, EV battery).
- **Cost to own:** Edmunds True Cost to Own, KBB 5-Year Cost to Own; **get insurance quotes by VIN/trim before buying.**
- **Depreciation:** iSeeCars model-level 5-year depreciation (average **41.8%**; trucks/hybrids best; EVs/luxury worst).

### 17.3 Reading listings (red flags)
| Flag | Reading |
|---|---|
| **Price far below comps** | Hidden branded title, damage, scam, or "internet price" with requirements; verify before traveling |
| **No VIN or blurry photos** | Hiding history/condition; ask for VIN and a walk-around video |
| **"Clean title" claimed in text but history shows brand** | Seller misrepresentation |
| **"Needs minor work"** | Quote the work; price it into value |
| **Shipped from another state quickly** | Possible flood/title washing; check title history |
| **Seller refuses a PPI** | **Walk.** |
| **Pressure ("another buyer coming")** | Tactic; verify condition anyway |
| **Owner's name not on title (curbstoner)** | Unlicensed dealer; potential title/odometer problems |
| **"Just serviced" without receipts** | Ask for invoices |
| **Odometer inconsistent with wear or history** | Check history report, maintenance records, pedals/seat |
| **CPO/"certified" labeling unclear** | Ask for the certification checklist and warranty terms in writing |

---

## §18. Value the Target and Build the Offer

### 18.1 The three numbers
1. **Market-value range** from §15 (comps + regression + guides + real offers).
2. **Payment ceiling** from §16 (total monthly cost you can carry).
3. **Walk-away OTD** = the **lower** of (value-range high end + any justified premium) and the OTD at your payment ceiling. **Write it down.**
- **Open** ≈ low end of the defensible range (justified by comps); **Target** ≈ midpoint adjusted for regime (§9.1).

### 18.2 The OTD method (dealer purchases)
1. **Shop 3–5 dealers by email/text** for the *specific VIN* or stock number: ask for an **itemized out-the-door quote** (vehicle price, rebates, doc fee, taxes, title/registration, each add-on, total).
2. **Compare OTD totals**, not monthly payments. In one 2025–26 dataset (~43,000 quotes), buyers who compared OTD quotes from multiple dealers saved an average **3–5%** (⚠️ vendor data). Ask each dealer to beat the best OTD in writing.
3. **Negotiate in this order:** (a) the **vehicle price** (against comps/ATP and days on lot), (b) **trade-in** (separately; see §22), (c) **financing** (beat your pre-approval), (d) **add-ons** (remove).
4. **Verify advertised incentives/rebates** and their qualification requirements (loyalty, college grad, financing with the captive lender). **"Market adjustment" markups** on hot models and **dealer-installed add-ons** are *negotiable or removable*; the **destination charge** appears on the window sticker and is rarely negotiable; **taxes and government fees** aren't.
5. **Doc fee:** negotiate the *total*; in capped states (e.g., California's $85) the fee is fixed; in uncapped states fees range from ~$300 to $1,000+.
6. **Don't take the car "home pending financing"** unless the contract states the financing is final (see **spot delivery/yo-yo** scams below).

**Email script (OTD request):** *"I'm ready to buy [year/trim/color, stock # or VIN] this week. Please send an itemized out-the-door price including vehicle price, rebates I qualify for, doc fee, taxes, title/registration and any dealer add-ons. I'm comparing quotes from [N] dealers and will buy from the best OTD. I'll arrange my own financing and have a pre-approval from [lender]."*

### 18.3 Negotiation by regime (§9.1 → `carval-market-analysis-and-timing`)
- **Hot/firm:** price near asking; be pre-approved; decide quickly *within your walk-away*.
- **Balanced:** negotiate 3–5% off asks on used; use competing OTD quotes; request removal of add-ons.
- **Soft/falling (late 2026 trend):** lower offers justified by comps and days on lot; target stale listings (60+ days, multiple cuts); consider waiting for model-year changeover on new cars.
- **Always:** *cite evidence* ("three comps within 150 miles at $X–$Y after adjusting for mileage; this unit has been listed 71 days").

### 18.4 Common dealer tactics and defenses
| Tactic | Defense |
|---|---|
| **Payment-focused negotiation ("what monthly payment do you want?")** | Say you'll negotiate OTD only |
| **Four-square worksheet** | Insist on price first, trade and financing separate |
| **Spot delivery / "yo-yo" financing** | The dealer calls days later saying financing "fell through" and demands a higher rate or more down. **Don't take delivery until the finance contract is final and signed; keep your pre-approval as a fallback; never agree to rewrite a signed contract at worse terms without legal advice (state rules vary).** |
| **Mandatory add-ons** | Ask for written proof they're required by law (they are not); refuse or negotiate OTD |
| **Fake urgency** | Walk; the same car or a better one will be available |
| **Lowball trade-in then high price** | Know your car's value (§22); get independent offers |
| **Advertised price excludes fees/"requires financing"** | Request itemized OTD in writing |

---

## §19. Under Contract: F&I, Inspection and Closing

### 19.1 Finance & insurance (F&I) products
| Product | Consider when | Notes |
|---|---|---|
| **Extended warranty / vehicle service contract (VSC)** | Unreliable/complex car out of warranty; you can't absorb a $3–5k repair | **Price is negotiable**; insist on a reputable administrator/insurer, review exclusions and claim process; compare with manufacturer plans; ask about cancellation/refund |
| **GAP** | Low down payment, long term, fast-depreciating car | Often cheaper through your insurer/credit union; refundable on payoff |
| **Maintenance prepay** | Rarely good math unless discounted | Compare to actual service costs |
| **Paint/fabric protection, VIN etching, nitrogen, "appearance packages"** | **Usually decline** | High markup, low value |
| **Tire/wheel, windshield, key replacement, dent repair** | Only if priced fairly relative to likelihood/cost | Check your insurance first |
| **Credit life/disability** | Usually decline | Term life/disability insurance is cheaper |
Dealer add-ons averaged **~$2,000** per deal in one quote study (vendor data): **itemize and decide each one separately; never accept a bundled "package."**

### 19.2 Inspection and verification before you sign
- **Pre-purchase inspection (PPI)** by an independent shop (**~$100–$250**; ⚠️ varies) on **any used car**, including CPO. For EVs: **battery health report**. For exotics/classics: marque specialist.
- **History report** (Carfax/AutoCheck/NMVTIS) *and* **NHTSA recall check by VIN**; verify **title status** on the actual title (§26).
- **Test drive** 30+ minutes including highway, cold start, parking-lot turns, A/C and heat, electronics.
- **Confirm paperwork:** VIN on car/title/bill of sale match; odometer statement; **lien status**; **keys/remotes**; manuals; service records.

### 19.3 Private-party purchase: step by step
1. **Verify the seller:** government ID matches the **name on the title**; VIN on the title matches the car (dash and door jamb); no lien (or a lien release process).
2. **Inspect:** PPI + test drive + history report.
3. **Agree price in writing:** bill of sale with date, price, VIN, odometer, "as is" language, both signatures.
4. **Payment:** **meet at the buyer's bank or seller's lender;** use a **cashier's check verified with the issuing bank** or a bank transfer you initiate at the branch. **Never wire to a stranger, use gift cards, or use "escrow services" the seller proposes** (common fraud).
5. **Lien handling:** if the seller still owes money, complete the transaction **at the lienholder** (payoff and title release) or use the lender's process.
6. **Transfer:** signed title, odometer disclosure, bill of sale; **register and pay sales tax at the DMV** (often due within days); get **insurance bound before driving**; temporary tags if required.

### 19.4 Online-retailer purchase
Verify the **return window** (company policy, not law), who pays return shipping, **inspection rights**, fees and the **actual condition report**; get an independent PPI if allowed; read the **registration/title timeline** and what happens if the car arrives with undisclosed damage.

---

## §20. Decision Rules for Common Buyer Situations

### 20.1 Keep the car you have vs replace it
`repair_or_replace(vehicle_value, repair_cost, expected_extra_years, replacement_monthly_cost, current_monthly_cost, expected_other_repairs_yr)`.
**Illustration:** value $9,000; repair $2,800 (31% of value); keep 3 more years with $700/yr other repairs and $200/mo current costs → **$12,100** vs replacing at $650/mo → **$23,400**. **Keep** if the repair is **< ~50% of value**, the repair fixes a root cause, and the car is otherwise sound. **The cheapest car is usually the one you already own**, absent safety issues or chronic failures.

### 20.2 Rolling negative equity into a new loan
Avoid when possible. Options: **keep driving** until the loan balance falls below value; **pay down principal** (extra payments); **sell privately** and cover the gap with cash/a personal loan (often cheaper than financing it at car-loan rates plus fees); **refinance** to a shorter term if rates allow. **Cost of rolling $6,884 (the Q2 2026 average) at 6.35% over 70 months: +$118/month and +$8,255 total** (toolkit), because the loan principal is higher *and* the new car depreciates on a larger base.

### 20.3 EV vs gas (running cost)
`ev_vs_ice()` with 0.30 kWh/mi, 80% home charging at $0.17/kWh, 20% public at $0.45/kWh, 30 mpg gas at $4.10: **EV $0.068/mi vs gas $0.137/mi → ~$826/yr savings at 12,000 mi** (placeholder inputs). **The savings don't automatically offset a higher price** (new-EV ATP $54,813): run `tco()` for both with your numbers, **don't subtract the federal credit (ended Sept 30, 2025)**, and **check state/utility incentives, home-charging installation cost, insurance and battery warranty.**

### 20.4 Lease vs buy
See §28.2 → `carval-diligence-risk-and-ownership-economics`. Short answer: leasing wins when the **residual is high** relative to what the car will actually be worth and the **money factor is low**; buying wins when you keep the car beyond the term or the residual is low.

### 20.5 Trade timing and the "payment treadmill"
The classic trap is trading every 3–4 years while still owing more than the car is worth. Each rollover adds interest and makes the next trade harder. **Break the cycle** with a **larger down payment**, a **shorter term**, or **holding the car** until you have equity.

### 20.6 Buying from out of state
Factor **transport cost**, **sales tax and registration in your state** (you generally pay your home state's tax at registration), **return/inspection rights**, and **PPI** by a shop near the car (get a remote PPI service if needed). Compare OTD in *your* state.

---

## §20A. Buyer Checklists

**Before shopping:** [ ] total monthly budget [ ] pre-approval(s) [ ] insurance quote [ ] shortlist with reliability/TCO [ ] value ranges (§15) [ ] walk-away OTD written.
**At the dealer/online:** [ ] itemized OTD quotes from 3+ [ ] trade handled separately [ ] financing beats pre-approval [ ] add-ons itemized and declined/accepted individually [ ] no spot delivery without final financing.
**Before signing:** [ ] PPI done [ ] history + recall check [ ] title status verified [ ] contract numbers match [ ] return terms in writing [ ] insurance bound.
**After:** [ ] registration/title tracking [ ] keep all documents [ ] schedule maintenance baseline [ ] review GAP/VSC cancellation options.
