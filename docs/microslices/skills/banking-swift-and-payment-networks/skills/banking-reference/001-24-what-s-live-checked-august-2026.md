---
id: skill-24-what-s-live-checked-august-2026-b926deb6ee
purpose: 24 what s live checked august 2026
source: src/vibey_tools/skills/plugins/banking-swift-and-payment-networks/skills/banking-reference/SKILL.md
requires: []
links: ["skill-25-misconceptions-bdb71ebae5"]
---

## §24. What's Live — checked August 2026

### 24.1 ⚠️ ISO 20022: the migration succeeded, and it isn't over
**⚠️ §8 → `banking-correspondent-swift-iso20022-and-governance`'s transition passing its hardest deadline — with a live one three months out.**

- **⚠️ COEXISTENCE ENDED 22 NOVEMBER 2025.** ⚠️ **Swift permanently retired legacy MT
  payment instruction messages from cross-border flows, making ISO 20022 the sole standard
  for CBPR+.**
- **⚠️ THE ADOPTION FIGURE IS STRIKING.** ⚠️ **Swift reports a 97% adoption rate after the
  cutover weekend, describing it as a very successful end of coexistence.** ⚠️ **Fedwire
  went ISO-native in July 2025, and reporting puts over 70 countries and nearly 200 market
  infrastructure initiatives on the standard.**
- **⚠️ THE NEXT HARD DEADLINE IS 14 NOVEMBER 2026, and it is the harder one.**
  ⚠️ **Fully unstructured postal addresses stop being accepted in CBPR+ payments — only
  fully structured or hybrid (town name and country code in dedicated fields) will pass.**
  ⚠️ **The interbank MT101 relay is also decommissioned in favour of pain.001 version 9.**
- **⚠️ WHY THE ADDRESS RULE IS DISPROPORTIONATELY DIFFICULT**: ⚠️ **it is not a messaging
  change but a DATA GOVERNANCE change reaching into KYC records and customer master data
  (§21 → `banking-compliance-security-and-remittance-costs`) — you cannot emit a structured address you never collected.**
- ⚠️ **The roadmap continues to 2027–28 for statements, direct debits, charges and
  investigations, with camt.110 and camt.111 replacing the MT19x/29x exception messages.**

> **⚠️ GOTCHA — "97% adoption" and "fully migrated" are different claims, and the gap is the
> story.** ⚠️ **Swift's own guidance addresses institutions still relying on CONTINGENCY
> PROCESSING or IN-FLOW TRANSLATION, urging them to plan full adoption in 2026 — and one
> analysis observes that the translation safety net arguably shaped behaviour, with many
> institutions leaning on conversion layers rather than re-architecting around native ISO
> 20022.**
> ⚠️ **Contingency conversion is also being charged for as of January 2026, which is the
> economic nudge.** **⚠️ So a bank can be "compliant" while capturing none of §8 → `banking-correspondent-swift-iso20022-and-governance`'s actual
> benefits, because the rich data is being manufactured at the boundary rather than carried
> end to end.**

**⚠️ The strategic reading** is that November 2025 was the syntax milestone and the value
comes later — ⚠️ **structured data enforcement, investigations modernization, and instant
payment interoperability.** ⚠️ **One vendor analysis claims 44% of banks will miss the next
deadline, which is a marketing figure from a firm selling migration services and should be
read as such — but the underlying point that address data is harder than message format is
correct.**
**⚠️ Sourcing note: the dates, the 97% figure and the roadmap come from Swift's own
documentation and from J.P. Morgan's client guidance, which agree.**

### 24.2 ⚠️ What is actually settling on blockchain rails — and it is mostly not XRP
**⚠️ §12 → `banking-ripple-xrp-ledger-and-honest-assessment`'s distinction becoming the central fact of the story, and §16 → `banking-ripple-xrp-ledger-and-honest-assessment`'s second structural
critique playing out.**

- **⚠️ THE PATTERN IN THE REPORTING IS CONSISTENT: institutions choose STABLECOINS over
  volatile bridge assets.** ⚠️ **Reporting states that Ripple's major 2026 institutional
  deals settled in RLUSD rather than XRP, attributing it to price volatility blocking
  compliance approval on large trades.**
- **⚠️ THE ILLUSTRATIVE CASE.** ⚠️ **A May 2026 pilot reportedly involving JPMorgan,
  Mastercard, Ondo and Ripple cleared a cross-border tokenized US Treasury trade on the XRP
  Ledger in under five seconds — ⚠️ but the settlement ran through RLUSD, with XRP covering
  only network fees of a fraction of a cent.**
  ⚠️ **That single example is §12 → `banking-ripple-xrp-ledger-and-honest-assessment`'s distinction in one transaction: the LEDGER was used,
  the TOKEN essentially was not.**
- **⚠️ THE NUMBERS, all reported and all from crypto-sector sources**: ⚠️ **RLUSD reportedly
  around $1.5–1.8 billion market cap and roughly 89% of the XRP Ledger's stablecoin market;
  ⚠️ approximately 40% of RippleNet institutions actively using XRP for ODL; ⚠️ and a
  record 19 million weekly XRPL transactions in March 2026 alongside a reported 80% decline
  in the share using XRP specifically for cross-border payments.**
- **⚠️ WHERE XRP STILL HAS A CASE, and it is a real one**: ⚠️ **thin corridors where
  stablecoin liquidity is shallow and large transfers would suffer slippage — SBI Remit's
  Japan-to-Southeast-Asia flows are the cited example.** ⚠️ **This is a narrower claim than
  the general one and it is more defensible.**

> **⚠️ GOTCHA — the company and the token can succeed independently, and §16 → `banking-ripple-xrp-ledger-and-honest-assessment` flagged this as
> the structural risk.** ⚠️ **A Forbes analysis puts the diagnostic cleanly: banks can use
> Ripple's platform without ever using XRP, settling in fiat or in RLUSD, and Ripple earns
> revenue either way.** ⚠️ **It offers a checkable indicator — total transaction FEES on the
> XRP Ledger remaining minimal relative to XRP's market capitalization, which it reads as
> the network not being used at the scale the valuation implies.**
> **⚠️ That is a falsifiable test rather than a narrative, which is why it is worth
> carrying.**

**⚠️ Meanwhile the incumbent moved** (§16 → `banking-ripple-xrp-ledger-and-honest-assessment`'s fifth critique): ⚠️ **reporting indicates SWIFT
is building its own blockchain-based shared ledger, targeting a live MVP in 2026 with 40+
banks.** ⚠️ **If the network-effect argument in §7 → `banking-correspondent-swift-iso20022-and-governance` holds, an incumbent-led shared ledger is
a serious competitive development.**
**⚠️ Sourcing warning, and it is the strongest in this file.** ⚠️ **Almost every source for
this subsection is crypto-sector media, some of it explicitly price-focused, and several
figures trace to single unverified reports.** ⚠️ **I have marked everything as reported.**
⚠️ **The DIRECTIONAL finding — institutions settling in stablecoins rather than volatile
bridge assets — appears consistently across sources with differing editorial positions,
including ones sympathetic to XRP, which is why I hold that part more firmly than any
specific number.**

---
