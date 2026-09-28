---
id: skill-the-five-systems-positioned-86d7be206d
purpose: the five systems positioned
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-start-here-and-the-five-systems/SKILL.md
requires: ["skill-how-this-pack-was-built-and-how-to-trust-it-18cccd4865"]
links: ["skill-learning-paths-depending-on-what-you-want-b8b86cc82d"]
---

## The five systems, positioned

| | **Bitcoin** | **Ethereum** | **Monero** | **PayPal** | **Stripe** |
|---|---|---|---|---|---|
| What it actually is | A settlement asset + PoW ledger | A programmable settlement platform | Privacy-preserving PoW currency | A two-sided account network + PSP | A developer-first PSP/aggregator |
| Native asset | BTC | ETH + the whole token universe | XMR | USD etc. (PYUSD on-chain) | None — moves fiat (and now stablecoins) |
| Who can censor/reverse | Miners (expensively); txs irreversible | Validators; txs irreversible | Miners; txs irreversible | **PayPal can**: freeze, reverse, hold | **Stripe can**: freeze, reserve, terminate |
| Finality | Probabilistic (~6 confs ≈ 1 hr) | ~13 min cryptographic finality | Probabilistic (~10 blocks ≈ 20 min convention) | Instant in-ledger, **days to cash out, months of chargeback tail** | Same fiat rails; payout T+1–T+2 typical |
| Programmability | Limited Script + PSBT/miniscript + Lightning | **Full smart contracts (EVM)** | Essentially none (by design) | REST APIs, Braintree, payouts | The broadest payment API surface |
| Privacy | Pseudonymous, fully public | Pseudonymous, fully public | **Private by default** (sender, receiver, amount) | Fully surveilled, KYC'd | Fully surveilled, KYC'd |
| Headline cost to accept money | On-chain: variable fee market (~sub-$1 typical in 2026's low-fee era but spikes); Lightning: ~0.01–0.05% routing | L1 ~sub-cent–$0.25 typical as of Sep 2026; L2s fractions of a cent | Negligible (cents) | 2.99–3.49% + $0.49 (US online, fee PDF eff. 1 Sep 2026) | 2.9% + $0.30 online cards (US) |
| "Developing on it" means | Node ops, wallets, PSBT/multisig, Lightning, BDK | Smart contracts (Solidity) + clients + L2s + DeFi | Daemon/wallet RPC, view keys, atomic swaps | Orders/Payouts/Subscriptions APIs, Braintree, PYUSD rails | PaymentIntents, Checkout, Connect, Billing, stablecoin stack |

**The one framing that organizes everything:**

- On the crypto side: **deployed code (or a held key) is money in public.** There is no chargeback and no one to call. Your failure modes are theft, loss, and protocol risk.
- On the fiat side: **money is data with an audit trail, a counterparty, and a regulator.** There *is* someone to call — and that someone can also freeze you, reverse you, and hold 90-day reserves. Your failure modes are idempotency bugs, webhook mishandling, reconciliation drift, and account risk.
- Monero sits deliberately at the far end of the crypto side: it buys fungibility and privacy at the price of regulatory exclusion from most regulated on-ramps.

---
