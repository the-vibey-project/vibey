---
id: skill-6-the-stablecoin-stack-bridge-privy-tempo-versioned-fast-moving-45b1497ada
purpose: 6 the stablecoin stack bridge privy tempo versioned fast moving
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-stripe/SKILL.md
requires: ["skill-5-money-movement-products-pricing-us-as-of-sept-2026-9a5b731519"]
links: ["skill-7-regulatory-backdrop-that-touches-stripe-builders-as-of-16-sep-2026-979e952651"]
---

## 6. The stablecoin stack: Bridge + Privy + Tempo — [VERSIONED, fast-moving]

- **Bridge** — stablecoin orchestration/issuance; **acquired for $1.1B (announced Oct 2024)**. Its **Open Issuance** platform (Oct 2025) powers custom stablecoins incl. MetaMask, Phantom, Hyperliquid's USDH, Sui's USDsui. **Feb 2026: OCC granted Bridge a conditional national trust bank charter** (Circle, Ripple and Paxos in the same cohort) toward federal stablecoin issuance/custody/reserve management ([GL Insight](https://www.glinsight.com/stripes-vertical-stablecoin-stack-bridge-tempo-and-a-1-5-take-rate/)).
- **Privy** — embedded-wallet infrastructure (custodial key management inside apps; Ramp's stablecoin accounts are custodied via Privy).
- **Tempo** — the payments-first blockchain Stripe co-developed with Paradigm. **Mainnet live March 2026**: EVM-compatible L1, sub-second finality, stablecoin-denominated fees (~$0.001 fixed), **no native token**. Validators include Visa, Stripe, Zodia Custody, MoneyGram; design partners: Mastercard, Deutsche Bank, Revolut, Nubank, Shopify, OpenAI, Anthropic ([Tempo blog](https://tempo.xyz/blog/stripe-and-tempo-stablecoin-settlement-for-global-money-movement/)).
- **April 2026**: Stripe's money-management APIs support stablecoin transfers on Tempo; businesses in 100+ countries can hold/send/receive stablecoins from Stripe — expanding into Connect payouts, Issuing and onramps.
- **Flagship customers**: **Deel** (June 2026) — contractor wallet for 1.5M contractors/150+ countries on the full stack (Bridge Open Issuance stablecoin DLUSD + Privy wallets + Tempo settlement; live in Argentina first) ([Stripe newsroom](https://stripe.com/newsroom/news/deel-and-stripe)); **Ramp** — stablecoin accounts + bill pay with up to 3.25% rewards on balances ([The Defiant](https://thedefiant.io/converge/tradfi-and-fintech/ramp-adds-stablecoin-accounts-and-bill-pay-on-stripe-stack)).
- **Economics**: 1.5% merchant take rate on near-zero settlement cost — an "interchange-shaped" margin opportunity at the PSP layer; competitive pressure from Circle's Arc and Mastercard's BVNK acquisition. Treat pricing as promo-fragile: the **0.8% promo ends 1 Jan 2027**.
- **Agentic payments**: Stripe co-authored **ACP** with OpenAI (Sept 2025) and launched **MPP** (agent pre-authorizes a spend limit, streams micropayments, Mar 2026); Shared Payment Tokens sit in the current preview API (§2). ⚠️ **Reality check**: OpenAI's Instant Checkout — the ACP flagship — was **retired 5 Mar 2026** after ~30 merchant integrations, and consumer adoption stayed low through its life. Build machine-readable catalogs and adopt a standard (don't roll your own agent-payment flow — that's how you inherit the fraud liability), but don't bet the roadmap on agent volume yet.

---
