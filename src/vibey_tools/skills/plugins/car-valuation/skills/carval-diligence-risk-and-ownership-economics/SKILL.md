---
name: carval-diligence-risk-and-ownership-economics
description: "Use when stress-testing a specific car or deal: pre-purchase inspection scope, history-report limits (Carfax, AutoCheck, NMVTIS), title brands and their discounts, recalls, physical red flags (flood, structural repair, odometer), EV battery health; fraud patterns (odometer rollback, title washing, VIN cloning, curbstoning, fake escrow, payment-screenshot scams, yo-yo financing); ownership economics (total cost of ownership and what dominates it, lease vs buy and the money-factor/residual math, EV vs gas running costs, repair vs replace, extended-warranty value); specialty cases (classic/collector, salvage/rebuilt, imports, rideshare/fleet); and consumer remedies (lemon laws, complaints, repossession basics)."
---

# Car Valuation and Market Research: Diligence, Fraud and Ownership Economics

> **Part 6 of 7** of the *Car Valuation and Market Research* reference (plugin `car-valuation`), covering §26–§30. Sibling skills: `carval-concepts-methods-and-market-structure` (§0–§4), `carval-market-analysis-and-timing` (§5–§9), `carval-valuing-a-specific-vehicle` (§10–§15), `carval-buyer-playbook` (§16–§20), `carval-seller-playbook` (§21–§25), `carval-reference` (§31–§35). Code: `scripts/carval.py` (`tco`, `lease_payment`, `lease_vs_buy`, `ev_vs_ice`, `repair_or_replace`, `negative_equity_months`, `gap_needed`).
>
> **Currency:** Diligence and fraud patterns are stable; the economics use **placeholder inputs** (rates, insurance, fuel). Replace them with your own quotes.

> **⚠️ Scope.** Educational; not mechanical, legal, insurance or tax advice. A pre-purchase inspection and a history report reduce risk; they do not eliminate it.

> **The three ideas:**
> 1. **⚠️ Diligence converts an estimate into a value.** Every finding ends in one of three outcomes: a price reduction (cost-to-cure plus risk margin), a repair/condition before purchase, or a walk. Never "note it and move on" (§26.4).
> 2. **⚠️ Running costs often exceed depreciation.** In the verified 5-year example, **running costs were ~53% of total ownership cost, depreciation ~30%, interest ~12%** (§28.1). Choosing a car on sticker price alone misses most of the cost.
> 3. **⚠️ A lease is a bet on the residual.** It beats buying only when the contractual residual is at or above what the car will actually be worth, or when the money factor is subsidized (§28.2).

---

## §26. Pre-Purchase Inspection, History and Verification

### 26.1 Pre-purchase inspection (PPI) scope
**Do it for every used car, including CPO.** Typically ~$100–$250 at an independent shop (⚠️ varies); use a **marque specialist** for luxury, exotic and classic cars.
| Area | What to check | Red flags |
|---|---|---|
| **Structure/frame** | Frame rails, unibody welds, suspension mounts, panel gaps, bolt marks on fenders/hood | Uneven gaps, repainted structural areas, frame straightening, sealer seams |
| **Paint/body** | Paint thickness, overspray, mismatched finish, trim fit | Repainted panels with no disclosure; fresh undercoating hiding rust |
| **Engine/drivetrain** | Cold start, leaks, fluid condition, belts/chains, compression/leak-down when warranted, codes | Rough idle, smoke, metal in oil, milky coolant, slipping/hard shifts |
| **Transmission/driveline** | Shift quality, fluid, CV boots, differential noise | Burnt fluid, shudder, delayed engagement |
| **Brakes/tires/suspension** | Pad/rotor/tire wear patterns, shocks/struts, alignment | Uneven tire wear (alignment/frame), warped rotors |
| **Electronics/ADAS** | Dash warnings, window/seat/HVAC, camera and radar function, **calibration after windshield/bumper work** | Disabled safety systems; DIY clears |
| **OBD-II scan** | Stored/pending codes, **readiness monitors** (recent resets) | Codes cleared recently; monitors "not ready" |
| **Flood/rust** | Under carpets, seat rails, trunk, door seals, silt/mud, musty smell, corroded connectors | Water lines, rust in unusual places, mismatched carpet |
| **Safety systems** | Airbag light, seat belts, SRS history | Airbag light, mismatched or non-OEM components |
| **EV/hybrid** | **Battery state of health (SoH)**, charging test (AC and DC), thermal system, coolant, software/recalls | Rapid capacity fade, charging errors, unresolved battery recalls |
| **Documentation** | VIN plates (dash/door/engine bay), keys, manuals, service records, window sticker | VIN mismatches, missing records, signs of tampering |
**Test drive** 30+ minutes: cold start, highway, bumps, tight turns, hill, A/C and heat, noises, steering pull.

### 26.2 History reports: what they show and what they miss
- **Carfax / AutoCheck** (commercial) and **NMVTIS** (federal database of title/brand/odometer data via approved providers) report **reported** events: title brands, accident/airbag deployment records, odometer readings, service records, owner counts, lien/theft flags, import/export.
- **What they miss:** accidents **never reported to insurance/police**, cash repairs, **private-party history**, work outside reporting networks. **A clean report ≠ a clean car**; a PPI is mandatory.
- **Use two sources** where the car is expensive; cross-check mileage entries for **anomalies** (backward jumps, long gaps).
- **Free checks:** **NHTSA recalls by VIN** (safercar/recalls site), **NICB VINCheck** (theft/salvage), state DMV title inquiries (varies).

### 26.3 Title brands (what they mean and how they affect value)
| Brand | Meaning | Value/financing/insurance effect |
|---|---|---|
| **Clean** | No brand | Baseline |
| **Salvage** | Declared total loss (not road-legal until repaired/inspected) | Heavy discount; many lenders/insurers won't cover |
| **Rebuilt/Reconstructed/Revived** | Salvage repaired and inspected | Commonly cited **20–40% below clean** (⚠️ verify by model); insurance/financing restricted |
| **Flood** | Water damage | **Avoid** unless specialist-inspected and priced for risk |
| **Junk/Parts only** | Not repairable for road | Parts/scrap value only |
| **Lemon law buyback** | Repurchased by the manufacturer for defects | Discount; disclosure required in many states |
| **Odometer discrepancy / not actual mileage** | Mileage unreliable | Significant discount; legal exposure |
| **Prior taxi/police/rental/lease** | Usage history | Condition expectations differ; may carry modest discount |
**Verify the brand on the actual title** and via NMVTIS: **title washing** moves a car through states with weaker brand rules to erase the label.

### 26.4 Convert findings into decisions
| Finding | Typical response |
|---|---|
| Safety/structural (frame, airbags, brakes, steering) | **Walk** or require repair by a reputable shop with proof; price in full |
| Mechanical (engine/transmission noises, leaks) | Get a **repair estimate**; price = estimate + risk margin; **walk if unknown** |
| Maintenance due (tires, brakes, fluids, timing belt) | **Cost-to-cure** price reduction |
| Cosmetic | Modest adjustment; don't spend negotiating capital |
| Title/odometer/VIN discrepancy | **Walk** (or resolve with documents before paying) |
| Open recall | Free repair at the dealer for most safety recalls: verify parts availability; some recalls are severe (do-not-drive) |
| EV battery SoH below expectations | **Reprice** by the replacement/risk cost; check warranty |
**Rule:** *request fewer, bigger items backed by estimates*.

### 26.5 Odometer and physical red flags
Wear that doesn't match mileage (pedals, steering wheel, driver seat), **digital odometer reset signs**, mismatched service stickers, **inconsistent maintenance receipts**, **new parts in an old car** (dash/cluster replacement without paperwork), and **history discrepancies**. If suspicious, **walk**.

---

## §27. Fraud and Scam Patterns

| Pattern | What happens | Defense |
|---|---|---|
| **Odometer rollback/cluster swap** | Mileage reduced to raise price | History report + wear check + service records; PPI shop reading module data |
| **Title washing / brand evasion** | Branded car retitled elsewhere | NMVTIS + physical inspection + insist on seeing the title |
| **VIN cloning** | Stolen car given a legitimate car's VIN | Compare VIN plates (dash, door, engine); check title/registration; walk if mismatched |
| **Curbstoning** | Unlicensed dealer poses as private seller | Seller's ID must match title; multiple listings; "title not in my name" = walk |
| **Fake escrow / shipping / "eBay Motors protection" sites** | Fake website asks you to wire money | Never use escrow proposed by the seller; use your bank; meet in person |
| **Deposit/too-good-to-be-true listings** | Seller abroad/military; low price | See the car in person; never pay before inspection |
| **Seller-side payment scams** | Fake cashier's checks, payment screenshots, overpayment/shipping, chargebacks | Verify funds at the bank; no payment-app transfers for large sums (§24.2 → `carval-seller-playbook`) |
| **Flood car laundering** | Hurricane-damaged cars moved out of state | PPI; check for corrosion/silt; history report |
| **Yo-yo (spot-delivery) financing** | "Financing fell through," demands worse terms after you drive off | Don't take delivery until financing is final (§18.4 → `carval-buyer-playbook`) |
| **Payment packing/add-on padding** | Add-ons inserted in contract | Read the contract; itemize; refuse (§19.1) |
| **Buy-here-pay-here traps** | High APR, GPS/starter interrupt devices, aggressive repossession | Compare with credit-union loans; read terms |
| **Fake "mechanic" or "inspection" referrals** | Seller sends you to their friend | Choose your own independent shop |
| **Used-car online listing cloning** | Photos copied from real listings | Reverse-image search; video call walkaround |
**Where to report:** your **state attorney general**, **FTC**, **NICB** (insurance fraud/theft), **DMV** and local police.

---

## §28. Ownership Economics

### 28.1 Total cost of ownership (TCO)
`tco(price, years, miles_per_year, resale_value, apr_pct, down, loan_months, insurance_yr, fuel_cost_per_mile, maintenance_yr, registration_yr, repairs_yr, sales_tax_pct, fees)`.
**Verified example:** $31,500 car, 5 years, 12,000 mi/yr, 20% down, 6.9% over 60 months, 6% tax, $500 fees, insurance $2,000/yr, fuel $0.13/mi, maintenance $600/yr, repairs $300/yr, registration $150/yr; resale = **58.3% of price** (placeholder retention).
| Component | 5-year total | Share |
|---|---|---|
| Depreciation | $13,135 | 30% |
| Interest | $5,111 | 12% |
| Sales tax + fees | $2,390 | 5% |
| Running costs (insurance, fuel, maintenance, registration, repairs) | $23,050 | **53%** |
| **Total** | **$43,686** | **$8,737/yr · $728/mo · $0.73/mile** |
**Lessons:** (a) **insurance and fuel** dominate running costs and differ widely by model; (b) the **cheapest-to-buy car isn't necessarily the cheapest to own**; (c) **holding longer** spreads depreciation and interest over more miles; (d) **sanity-check** against published per-mile ownership costs (AAA, Edmunds, KBB) for your class.

### 28.2 Lease vs buy
**Lease math:** monthly = **depreciation fee** `(cap cost − residual)/term` + **rent charge** `(cap cost + residual) × money factor`; **APR ≈ money factor × 2,400**; tax rules vary by state.
**Verified example:** $36,000 MSRP, 58% residual ($20,880), 36 months, MF 0.0027 (**6.48% APR-equivalent**), $2,000 cap reduction, $695 acquisition fee, 6% tax → cap cost **$34,695**; depreciation fee **$383.75**; rent charge **$150.05**; **$533.80/mo pre-tax; $565.83 with tax**.
**Versus buying the same car** (36-month loan at 6.9%, $2,000 down, car worth **70% of MSRP** at month 36 per the placeholder retention curve):
| Metric | Lease | Buy |
|---|---|---|
| Monthly | **$543** | **$1,115** |
| Total cash over 36 months | $21,562 | $42,135 |
| **Net cost after resale/equity** | **$21,562** | **$16,867** |
| Net incl. 4% opportunity cost on down payments | $21,811 | $17,117 |
**Why buying won here:** the contractual **residual (58%) was below the car's likely market value (70%)**; the lessor captures that equity. **Leasing wins when:** the **residual is high** (manufacturer-subsidized), the **money factor is subsidized** (lease cash/low MF), you **change cars every 2–3 years**, you drive **within the mileage allowance**, and (business use) tax treatment helps. Experian data (Q2 2026, via a secondary summary) shows a new lease averaging about **$148/month less** than a new loan: **lower payment, no ownership.**
**Negotiate:** the **cap cost** (like a purchase price), the **money factor** (ask for the buy rate), the **residual/miles**, and **fees** (acquisition, disposition); **avoid** rolling negative equity or add-ons into the lease; **check early-termination and wear terms**; **GAP** is usually included.

### 28.3 EV vs gas running costs
`ev_vs_ice()` with 0.30 kWh/mi; 80% home charging at $0.17/kWh and 20% public at $0.45; gas car 30 mpg at $4.10/gal: **EV $0.068/mi vs gas $0.137/mi → ~$826/yr saved at 12,000 mi.**
**What the running-cost saving must overcome:** a higher purchase price (new-EV ATP **$54,813** vs industry **$50,089**), possible **faster depreciation**, **home-charger installation**, **state EV registration surcharges** (many states charge them), insurance differences, tire wear and public-charging dependence. **Federal EV credits ended Sept 30, 2025.** Run `tco()` for both with your inputs; the EV wins more often with **high mileage, cheap home electricity and low purchase prices.**

### 28.4 Repair vs replace
See §20.1 → `carval-buyer-playbook`. **Rule of thumb:** repair when the cost is **< ~50% of value**, it fixes a root cause, and the car is otherwise sound; consider **replacement** when repairs recur (>$1,500–$2,000 a year), safety is compromised, or the car is near a major-cost threshold (transmission, head gasket, rust-through) *and* worth less than the repair.

### 28.5 Warranties and extended service contracts
- **Factory warranty** (bumper-to-bumper, powertrain, battery) and **CPO** coverage: know *what's left* (by VIN) and whether it's **transferable** (some are, with fees).
- **Extended warranty (VSC) value test:** expected claim cost vs price; **reliable models** rarely repay; **luxury/complex cars** sometimes do. **Check:** exclusions, deductible, labor rate, claim approval process, **repair-shop choice**, cancellation refund, **underwriter quality**. A cheaper alternative: **self-insure** by putting the same amount into a repair fund. **Price is negotiable**; get quotes from the manufacturer and independent providers.

### 28.6 Insurance as a valuation factor
Insurance cost varies by **model, trim, ZIP, driver profile** and **repair cost/theft rates**; **get quotes before buying**; EVs/trucks/luxury can be much costlier; **higher deductibles** and **usage-based programs** reduce cost with trade-offs. For total losses, see §25.3 → `carval-seller-playbook`.

---

## §29. Specialty Cases

### 29.1 Rideshare, fleet and high-mileage use
**Mileage** drives depreciation and repair rates; **mileage-based adjustments flatten** at high mileage; **insurance** must cover commercial use; **TCO per mile** matters more than payment.

### 29.2 Salvage and rebuilt purchases
Only with **expert inspection**, **photos of the original damage** and repair receipts; **check insurability and lending** before buying; **price at a substantial discount** (§26.3); **resale will be difficult**.

### 29.3 Classic and collector cars
- **Valuation:** **condition-graded values** (Hagerty #1–#4 as in §14.4 → `carval-valuing-a-specific-vehicle`), **documented provenance**, **originality and matching numbers**, mileage, options, **rust/frame**, restoration quality. **Overrating condition** is the most common error.
- **Ownership costs:** storage, **agreed-value insurance**, specialized maintenance, parts scarcity, registration/emissions exemptions, transport; budget **~1–3% of value per year** for upkeep and insurance in many cases (⚠️ rule of thumb; varies widely).
- **Market (Oct 2026):** collector-car market is soft (Hagerty Market Rating near ~15-year low; broad softness under $250k), with **selective strength** for trophy cars and some analog-era modern classics (Hagerty's 2026 "Bull Market List" focuses on 1990s–2000s cars; ⚠️ these are forecasts, not guarantees).
- **Buying approach:** *buy the best example you can afford*, **PPI by a marque specialist**, **verify documentation**, use **auction results with fees normalized**, and **don't treat a car as an investment.**
- **Selling approach:** match the **channel** to the car (auction, consignment, private), **document** everything, **expect fees** (buyer's premium/seller's fees), and **price to recent sales**, not asking prices.

### 29.4 Imports and gray-market cars
The **25-year rule** allows importation of certain older foreign-market vehicles; **title, registration and emissions** rules vary by state; **parts and service** can be limited; **valuation uses market-specific comps**; confirm **customs/DOT/EPA** compliance and **title history**.

### 29.5 Other vehicles
Motorcycles, RVs, boats and heavy trucks use different guides (e.g., J.D. Power for RVs/motorcycles, specialty price guides) but the **same method**: comps, adjustments, inspection, history, channel.

---

## §30. Remedies, Complaints and When Things Go Wrong

- **Lemon laws (state):** typically cover **new** vehicles (some used/leased) with a **substantial defect** not fixed after reasonable attempts within a **defined period/mileage**; remedies include **refund or replacement**; **document every repair visit** and send **written notices** as required.
- **Dealer misrepresentation:** keep **ads, texts, emails, buyer's order and Buyers Guide**; complain to the **state attorney general, DMV dealer board and FTC**; consider **small claims** or an attorney for large losses; **arbitration clauses** in the contract may apply.
- **Private-sale disputes:** **as-is** language limits warranty claims but not fraud; **small claims** is the usual venue.
- **Recalls:** repairs are **free** at authorized dealers; **document** open recalls and requests; if the dealer delays, escalate to the manufacturer and NHTSA.
- **If you can't make payments:** **contact the lender early** (deferrals, modifications, refinancing); **voluntary surrender or repossession** leaves you owing the **deficiency** (loan balance minus auction proceeds plus fees) in most states; state rules on notice and redemption vary; **seek a nonprofit credit counselor or legal aid** before it escalates.
- **Total loss dispute:** see §25.3 → `carval-seller-playbook`.

---

## §30A. Deal-Stress Template (5 minutes)

1. Value range (§15) and walk-away OTD (§18). 2. PPI and history findings → cost-to-cure total. 3. Title/odometer/VIN verified (§26). 4. Insurance quote and recall check. 5. TCO per year/mile (§28.1) vs the alternative car. 6. Loan: APR, term, **months until positive equity** (`negative_equity_months()`), GAP need. 7. Exit: what is this worth in 3 years? (retention curve, §9.4). 8. **Verdict:** buy / buy at $X / walk; name the **single biggest risk**.
