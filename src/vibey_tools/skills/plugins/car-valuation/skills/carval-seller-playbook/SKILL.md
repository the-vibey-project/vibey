---
name: carval-seller-playbook
description: "Use when selling or trading in a car: payoff and equity (including being underwater), choosing the channel (trade-in with state sales-tax credit, instant online offers, private party, consignment, auction) by net cash, price and effort, setting a list price and a floor, prep that pays (detail, records, cheap fixes, honest disclosure), photos and listing text, screening buyers, safe test drives and payment, the title/bill-of-sale/release-of-liability process, payment and escrow scams, and special cases (leased cars, total-loss insurance disputes, estate vehicles, non-running, EV battery reports, classics)."
---

# Car Valuation and Market Research: The Seller Playbook

> **Part 5 of 7** of the *Car Valuation and Market Research* reference (plugin `car-valuation`), covering §21–§25. Sibling skills: `carval-concepts-methods-and-market-structure` (§0–§4), `carval-market-analysis-and-timing` (§5–§9), `carval-valuing-a-specific-vehicle` (§10–§15), `carval-buyer-playbook` (§16–§20), `carval-diligence-risk-and-ownership-economics` (§26–§30), `carval-reference` (§31–§35). Code: `scripts/carval.py` (`channel_values`, `sell_net`, `tradein_tax_credit_value`, `retention_curve`, `repair_or_replace`).
>
> **Currency:** Procedures are stable; the **channel spreads in §22 are illustrative placeholders**; get real offers. Title/transfer rules are state-specific.

> **⚠️ Scope.** Educational; not legal or tax advice. DMV procedures, release-of-liability rules, lien-payoff processes and sales-tax treatment of trade-ins vary by state.

> **The three ideas:**
> 1. **⚠️ Compare channels by net cash after payoff, time and risk, not by headline price.** In the example below, a private sale beat a trade-in by only ~$300 after costs where the state gives a trade-in tax credit, but by ~$1,450 where it doesn't (§22).
> 2. **⚠️ Get 3 real offers first.** They set your floor, calibrate your valuation and cost you an hour. Then decide whether the extra price from a private sale is worth the work and fraud risk.
> 3. **⚠️ Most seller losses are process failures:** paying off the wrong amount, signing the title wrong, releasing the car before funds clear, or leaving liability with you. Follow the checklist (§24).

---

## §21. Decide to Sell: Equity, Timing and Housekeeping

### 21.1 Know your payoff and equity
1. **Ask the lender for a 10-day payoff letter** (with a per diem). Equity = realistic sale value − payoff.
2. **If equity is positive:** any channel works; maximize net. **If negative (underwater):** see §25.1; avoid rolling it into the next loan (§20.2 → `carval-buyer-playbook`).
3. **Lien and title:** with a lien, the lender holds the title (or electronic lien). The buyer's money must pay the lender first; **plan the transaction at the lender's branch** or use its payoff process (§24.3).

### 21.2 Timing
- **Depreciation clock:** a typical car loses roughly **1–1.5% of value per month** (age, mileage, market); in a softening wholesale market the cost of waiting is higher (§9.4 → `carval-market-analysis-and-timing`). **Sell before:** a mileage threshold (60k/100k/150k), warranty expiry, a redesign of your model, or a major service due (timing belt, transmission service) *if* you'd rather not fund it.
- **Season:** spring (tax-refund season) is typically strongest; **fall softens**. The Manheim index peaked in March 2026 and slid through summer (§9.3).
- **Compare to keeping:** use `repair_or_replace()` and the TCO model (§28).

### 21.3 Housekeeping before listing
Remove personal data: **unpair phones, clear infotainment/navigation history, log out of connected-car apps, delete garage-door/toll/EV-charging accounts**, remove toll transponders and parking permits, **factory-reset** the head unit where possible, and **transfer or cancel** connected services (EV subscriptions, remote start). **Do not cancel insurance until the sale is complete and the title is transferred (and plates handled per state rules).**

### 21.4 Taxes (US federal, general)
- A **personal-use car sold at a loss is not deductible**; a gain is theoretically taxable but rare (cars usually sell below purchase price); **collector cars** can produce taxable gain (consult a CPA).
- **Business-use** vehicles have depreciation recapture; keep records.
- **Sales tax:** the *buyer* pays tax at registration; in states that tax net of trade-in, **your trade-in saves the buyer tax**, which is part of the trade-in's value (§22).

---

## §22. Choosing the Channel and Setting the Price

### 22.1 The value chain (illustrative; the spreads are placeholders)
Starting from a **triangulated informal value of ~$21,390** for the §15 example car (dealer retail ≈ $22,676):
| Channel | Illustrative price | Notes |
|---|---|---|
| **Dealer retail** (what a dealer asks) | $22,676 | Not available to you |
| **Private party** | $21,315 (−6% from retail) | Highest realistic seller price |
| **Instant offer** (CarMax, Carvana, KBB Instant Cash Offer, etc.) | $19,501 (−14%) | Time-limited; subject to inspection |
| **Dealer trade-in** | $19,048 (−16%) | May carry a tax advantage in some states |
| **Wholesale/auction** | $18,141 (−20%) | What dealers can pay and still profit |
**⚠️ These percentages move with the market:** the spread **narrows when used demand is hot and wholesale rises**, and **widens in a falling market**; it also varies by car (popular models have thin spreads; unusual models wide). **Replace with real quotes.**

### 22.2 Net cash comparison (toolkit example; payoff $15,000)
| Channel | Price | Tax credit | Costs (listing/prep/time/risk) | **Net after payoff** |
|---|---|---|---|---|
| **Trade-in (state credits trade-in value at 6% tax)** | $19,048 | +$1,143 | $0 | **$5,190** |
| **Instant offer** | $19,501 | $0 | $0 | **$4,501** |
| **Private party** | $21,315 | $0 | $813 (listing $150, prep $250, 8 hrs @ $25, 1% risk haircut) | **$5,502** |
- **Result:** private beats trade-in by **~$312** (credit state) or **~$1,454** (no credit); it beats the instant offer by ~$1,000. **If you value your time at more than ~$40/hour, or you dislike the fraud risk, the trade-in/instant offer can be the rational choice.**
- **Where trade-in wins decisively:** a state with a trade-in tax credit **and** a purchase of a new car in the same transaction; a car with condition problems that an inspection will expose; a tight timeline.
- **Where private wins decisively:** a popular, clean, well-documented car; a hot market; you're comfortable with the process.

### 22.3 Offers first, then price
1. **Collect 3 offers** (two instant-offer services + one local dealer). Record price, **expiration**, inspection conditions and payoff handling.
2. **Compute your private-party range** (§15) and **list at the upper-middle** of it (market regime decides: firm → near the top; soft → near the middle).
3. **Floor price** = the best written offer (net of any tax credit) + a premium for the extra work and risk (~$500–$1,000). **List with a plan:** if no serious offer at your floor+ within 2–3 weeks, take the best instant offer or drop the price.
4. **Price bands and wording:** buyers filter by price bands ($20k, $22.5k…); price just under a band edge; "OBO" signals flexibility but invites low offers; "firm" can deter inquiries.

### 22.4 Price-adjustment rules (heuristics)
| Observation | Likely cause | Action |
|---|---|---|
| Few views (first 2–3 days) | Photos/title/price band | Improve photos and title; recheck comps |
| Views but few messages | Price high vs comps | Cut 2–3% |
| Messages but no showings | Unclear description or flagged risk (title, history) | Add documentation (history report, records) |
| Showings, no offers | Condition issues vs. alternatives | Fix cheap defects or cut price |
| Many offers | Priced low | Raise price/run best-and-final (private) |
**Cut decisively** (a step that moves you into another price band) **rather than tiny weekly cuts**; each re-list resets visibility on some platforms.

---

## §23. Prep: What Pays and What Doesn't

### 23.1 Spend order (highest expected return first)
1. **Professional detail** (interior, exterior, engine bay; ~$150–$400 in many markets; ⚠️ varies). **Highest ROI.**
2. **Assemble records:** service receipts, window sticker, manuals, **both keys/fobs**, tire and brake history, recall completion notices, **history report**, emissions/inspection certificates if required.
3. **Fix cheap visible defects:** bulbs, wipers, small chips, a failed **warning-light** cause (diagnose; **never clear codes to hide a problem**: monitors reveal recent resets and it can be a misrepresentation), paintless dent repair on door dings, windshield chips, curb-rash repair if cheap.
4. **Tires/brakes:** buyers deduct the replacement cost (often more); if tires are near the wear bars, a **price adjustment** may be cheaper than new tires; **new brakes** only if needed for safe test drives.
5. **Avoid:** major mechanical repairs or full repaints before sale unless the repair cost is clearly less than the value gain (usually it isn't); **modifications** rarely add value.
6. **Disclose** known defects and history honestly; document them in the ad and bill of sale. **Fraud claims are far costlier than a price reduction.**

### 23.2 Photos and listing text
- **20–30 photos in daylight on a clean car, neutral background:** all four corners, wheels, interior front/rear, cargo, **odometer**, **VIN plate**, engine bay, tire tread, any damage, and key features (screens, driver assist).
- **Video walk-around/engine start** reduces no-shows.
- **Text:** year/trim/engine/drivetrain, **mileage, title status (clean/branded), number of owners, accident history, maintenance, recent work with receipts, known issues, reason for selling, price, payment methods accepted, how to contact.** Avoid "no lowballers" and capital letters; **include VIN** (serious buyers will ask anyway).
- **EVs:** include a **battery health report** (state of health), charging equipment included, warranty remaining.

---

## §24. The Sale: Process, Safety and Paperwork

### 24.1 Screening buyers
- Reply only on the platform or by phone; **ignore "I'll send a courier/shipper" and "overpayment" offers**, buyers who won't see the car, and anyone asking for the VIN **plus** your personal data, a code sent to your phone, or an upfront fee.
- **Test drives:** meet in a **public place** (police-station "safe exchange" zones where available); **photograph the driver's license** and proof of insurance; ride along; **keep the keys in your control**; set a route.

### 24.2 Payment (the part where sellers get defrauded)
| Method | Verdict |
|---|---|
| **Cash** | Acceptable for modest amounts; **count and verify at the bank**; counterfeit check there |
| **Cashier's/certified check** | **Verify with the issuing bank** (call a number you look up; don't use the number on the check); **complete at the bank branch** so funds are confirmed before you release the title/keys; fake cashier's checks are common |
| **Bank wire/transfer** | Acceptable *only after* funds show as **cleared and available** in your account (verify in person at your bank) |
| **Zelle/Venmo/Cash App/payment apps** | **Avoid for large sums**: limits, reversals, fraud; **fake "payment pending" screenshots** are a common scam. Never release the car on a screenshot |
| **"Escrow" or "vehicle protection" service the buyer proposes** | **Typically a scam**; use a known bank or an escrow provider *you* select |
**Never release the car, title or keys until funds are verified.**

### 24.3 Paperwork (state rules vary: check your DMV)
1. **Bill of sale:** date, price, buyer/seller names and addresses, **VIN, odometer reading**, "**sold as-is, no warranty**," both signatures; **make two copies and photograph them.**
2. **Title:** sign **exactly** as your name appears; **don't leave the buyer's name blank ("open title")**; fill the **odometer disclosure**; if there's a lien, **complete the transaction at the lender** (payoff and release) or follow the lender's electronic-title procedure.
3. **Release of liability / notice of transfer:** file with your DMV **immediately** (online in many states). **This ends your responsibility for tickets, tolls and accidents after the sale.**
4. **Plates:** removal/transfer rules differ (some states keep plates with the seller; some with the car).
5. **Insurance:** cancel (or move to the new car) **only after** the title transfer and release are done; **keep records** (copies of title, bill of sale, release confirmation, buyer ID) for several years.
6. **After:** remove toll tags, remote-start accounts, subscriptions; return/cancel registration if required.

### 24.4 Handling trade-ins at a dealer
- **Separate the trade from the purchase:** agree the new-car OTD first, then negotiate the trade (or have the dealer quote it in writing beforehand).
- **Compare** with your instant offers; **account for the sales-tax effect** (§4.4 → `carval-concepts-methods-and-market-structure`).
- **Payoff:** the dealer pays your lender; **verify with the lender** that the payoff was received and the lien released (sometimes it takes days; keep paying until confirmed).
- **Negative equity:** it's added to the new loan (§20.2 → `carval-buyer-playbook`).

### 24.5 Instant-offer services
Provide VIN, mileage, **honest condition and history**; the **offer is conditional on in-person inspection**: undisclosed damage lowers or voids it. **Offers expire** (often ~7 days). Payment may be by check or deposit; **confirm lien payoff handling and timing**, and who keeps the title.

---

## §25. Special Seller Situations

### 25.1 Underwater (owe more than it's worth)
Options: **keep driving** and pay down; **pay the difference** in cash (often the cheapest if you must sell); **personal loan** to cover the gap (compare APR vs car-loan rate); **sell privately** (higher price shrinks the gap); **refinance** to a shorter term; **GAP refund** after payoff if you bought GAP; **avoid** rolling into a new loan unless unavoidable (§20.2).

### 25.2 Leased cars
You can't just sell: the lessor owns it. Options: **lease buyout** (residual + fees; compare to market value; **some lessors restrict third-party buyouts**, and dealers may take the car's equity), **lease transfer** (via assumption services; check rules), **early termination** (expensive), or **return** at term end (inspect/wear charges). If **market value exceeds the buyout price**, you hold **positive equity** (common when used prices are high).

### 25.3 Total loss and insurance-ACV disputes
If insurance totals your car, the **actual cash value (ACV)** is based on comps adjusted for mileage/condition. **To dispute:** gather **same-trim comps within 100–250 miles** (and sold prices where possible), **maintenance receipts and recent upgrades** (new tires, battery), clear photos; request the **valuation report** and **challenge each comp's adjustments**; invoke the policy's **appraisal clause** or your state's rules if needed. You can **keep the salvage** (value deducted) in some cases; a **rebuilt title** follows.

### 25.4 Estate and inherited vehicles
Obtain **legal authority** (letters testamentary/administration or state small-estate process) before selling; transfer the title via the DMV's estate procedure; **get a date-of-death value** for tax basis if the vehicle is valuable (a stepped-up basis applies; consult a CPA); insure the vehicle while it sits; consider **auction/consignment** for classics.

### 25.5 Non-running, damaged, or high-mileage cars
Sell to **salvage/junk buyers or parts yards** (get 3 quotes; confirm they handle title and removal; avoid upfront fees); **disclose "not running," damage and title status**. Salvage-brand disclosures are legally required in most states.

### 25.6 EVs and hybrids
Include a **battery health (SoH) report**, charging gear, warranty status and software/subscription transfer information; EV buyers are sensitive to battery uncertainty, and a **documented high SoH** can support the price. **Adjust for regional gas prices and incentives** (§9).

### 25.7 Classics and collectibles
Choose **specialist auction (BaT, Mecum, Barrett-Jackson)**, **dealer consignment**, or **private sale**; price using **Hagerty condition-graded values** and **recent comparable sales** with normalized fees; document **provenance, originality, restoration receipts**; use **escrow** for large transfers; consider **transport and insurance** during the sale; **state/tax rules for collectors** can differ.

### 25.8 Disputes after the sale
Keep records; "**as is**" language limits warranty claims but doesn't cancel fraud/misrepresentation claims; **small claims** handles most disputes; if the buyer claims you misrepresented, your **ad, texts and bill of sale** are your evidence. **Document the sale thoroughly** and **file the release of liability.**

---

## §25A. Seller Checklists

**Before listing:** [ ] payoff letter [ ] 3 offers (instant + dealer) [ ] value range (§15) and floor [ ] records/keys/manuals gathered [ ] detail + cheap fixes [ ] 25+ photos + video [ ] honest ad with VIN, title status and flaws.
**During:** [ ] screen buyers [ ] public meetups, ID/insurance for test drives [ ] no payment apps for large sums [ ] funds verified at the bank before release.
**Closing:** [ ] bill of sale (as-is, odometer, VIN) ×2 [ ] title signed correctly (no open title) [ ] lien released/payoff confirmed [ ] **release of liability filed** [ ] plates handled [ ] insurance changed after transfer [ ] records saved.
