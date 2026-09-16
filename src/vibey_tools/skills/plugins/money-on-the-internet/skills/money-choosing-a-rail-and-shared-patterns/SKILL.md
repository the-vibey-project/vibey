---
name: money-choosing-a-rail-and-shared-patterns
description: "Use when choosing between Bitcoin, Ethereum, Monero, PayPal and Stripe for a concrete job, when you need the decision heuristics and the merchant-of-record question, the four engineering patterns that transfer across every rail, a sequenced study roadmap, or the canonical documentation shelf. Companion to the other money-on-the-internet skills."
---

# Choosing a Rail: Decision Guide, Shared Patterns, and Study Roadmap

> **Part 7 of 7** of the *Money on the Internet* reference (plugin
> `money-on-the-internet`), covering §1–§5. Sibling skills:
> `money-start-here-and-the-five-systems` (how to read the pack, the five systems positioned side by side, learning paths),
> `money-bitcoin` (§1–§7 — UTXOs, policy vs consensus, wallets, Lightning, mining economics, Core development, the v30 fight),
> `money-ethereum` (§1–§5 — the account model, proof of stake, upgrades, using it, Solidity/Foundry/DeFi/security),
> `money-monero` (§1–§7 — the privacy stack, FCMP++, the Qubic affair, access and delistings, daemon/wallet development),
> `money-paypal` (§1–§6 — what it is, using it, the Sept 2026 US fee schedule, PYUSD, the APIs, PayPal vs Stripe),
> `money-stripe` (§1–§7 — the PaymentIntent model, integration patterns, compliance, pricing, the Bridge/Privy/Tempo stack),
> Section numbers are **per skill** here, not shared across the set: each chapter is a
> self-contained system. A reference written as §N → `skill` points at that skill's own §N.
>
> **Currency:** compiled 16 September 2026. The heuristics and the four transferable patterns are **[DURABLE]**; every figure in the §1 side-by-side is **[as of 16 Sep 2026]** and expires.
>
> **Not investment, legal, tax, or compliance advice.** The regulatory sections tell you what
> to ask your counsel, not what your obligations are.

> **⚠️ Start from the job, not the technology. Most "should we take crypto?" questions are answered by the stablecoin row, not the chain rows.**
>
> **⚠️ GOTCHA** boxes and the pack's **[DURABLE]** / **[as of …]** / **[CONTESTED]** tags mark
> what is safe to learn once and what must be re-verified.
>
> **The three ideas that organize this document:**
> 1. **⚠️ THE FOUR PATTERNS TRANSFER EVERYWHERE**
>    **Idempotency, webhook/event handling, reconciliation, and explicit state machines are the same problem on every rail. Learn them once and the specific API is detail.**
> 2. **⚠️ MERCHANT-OF-RECORD IS A LIABILITY DECISION, NOT A PRICING ONE**
>    **Who is the seller of record determines who owns tax, chargebacks and compliance. It is the question most integrations decide by accident.**
> 3. **⚠️ THE MODERN ANSWER TO "ACCEPT CRYPTO" IS USUALLY STABLECOIN ACCEPTANCE**
>    **Via a PSP's stack rather than self-hosted nodes. The chain skills matter for building *on* the protocol, not for taking payment.**

---

## 1. Side-by-side (all dated claims are "as of 16 Sep 2026")

| Dimension | Bitcoin | Ethereum | Monero | PayPal | Stripe |
|---|---|---|---|---|---|
| Settlement finality | ~probabilistic; 6 conf ≈ 1 h | ~13 min cryptographic | ~20 min convention (10 blk) | Ledger-instant, fiat behind it | Same |
| Reversible by operator? | No | No | No | **Yes** — disputes, holds, freezes | **Yes** — disputes, reserves, termination |
| Typical fee to accept $100 (US) | on-chain: sub-$1-ish in 2026's fee regime, spiky; LN ~0.01–0.05% | $0.003–0.25 L1 typical; L2s fractions of a cent | cents | $3.98 (3.49%+$0.49) | $3.20 (2.9%+$0.30); stablecoin payout 1.5% |
| Programmability | Script, PSBT, miniscript, Lightning | Full EVM | None | REST APIs + PYUSD contracts (ETH/SOL…) | Everything: Payments/Billing/Connect/Issuing/Tax + stablecoin stack |
| Privacy | Pseudonymous/public | Pseudonymous/public | **Default-private (ring-16, RingCT, stealth)** | KYC institution | KYC institution |
| Custody model | Self or custodian (ETFs) | Self/smart accounts/custodian | Self | PayPal custodies | Stripe custodies |
| Regulatory temperature (Sep 2026) | ETFs live; CLARITY failed 15 Sep; strategic-reserve bills pending | Same + GENIUS governs its stablecoin economy | **Coldest**: EU AMLR bar effective Jul 2027; India FIU directive; EEA delisted on Kraken | Licensed money transmitter; PYUSD under GENIUS regime | Same, plus Bridge's conditional OCC trust charter (Feb 2026) |
| Dev maturity | v31 Core, BDK/LDK mature, dev docs scattered | Best-in-class tooling (Foundry/HH3, viem) | monerod/wallet-rpc solid; library ecosystem thin | REST v2 + Braintree mature | Deepest API surface; best docs in payments |
| Failure mode you're insuring | Key loss, protocol risk, mempool policy shifts | Contract bugs, key theft, phishing | Exchange illiquidity, reorgs, regulation | Chargebacks, holds, freezes | Same + platform/price risk |

## 2. Decision heuristics

- **Selling online, mainstream customers** → Stripe Checkout/Payment Element as primary; **add the PayPal button** (and wallets) for conversion. Digital goods sold globally: price **Managed Payments / an MoR** (Paddle etc.) before hand-rolling tax — VAT/sales-tax nexus is the cost everyone discovers late.
- **Marketplace / paying third parties** → Stripe Connect (or PayPal for Marketplaces / Adyen for Platforms). Building the money movement yourself = money-transmitter licensing; almost never the right call.
- **Customers want to pay in crypto** → 2026 default: **stablecoin acceptance via a PSP** (Stripe ≥1.5% or PayPal "Pay With Crypto" 1.5%) — you get dollars, no keys, no reorg handling. Self-custodial acceptance is only worth it when: you specifically serve crypto-native customers, want no intermediary fee/censorship, or operate where PSPs won't have you. If so: accept **Bitcoin via Lightning** or **a major stablecoin on a mature L2**; treat Monero acceptance as a deliberate privacy/regulatory posture, not a feature checkbox.
- **You need actual privacy (donations under duress, political edge cases, fungibility)** → Monero, self-custody, P2P acquisition, and go in eyes-open about the shrinking regulated perimeter (Kraken US still lists XMR; Binance/Coinbase do not; EU institutions exit by Jul 2027).
- **Building *new* money infrastructure** → the crowded middle is stablecoins: Bridge Open Issuance / PYUSDx / GENIUS-regulated issuance, settling on Ethereum L2s or purpose chains like Tempo. The durable edges are unchanged: BTC as the censorship-resistant reserve asset; XMR as the privacy primitive.
- **Never make any single PSP existential**: secondary PSP, payout discipline, cash buffer. Applies identically to PayPal, Stripe, Square, Adyen.

## 3. The four engineering patterns that transfer everywhere

1. **Idempotency keys derived from business attempts, persisted before first call** — Stripe `Idempotency-Key`, PayPal `PayPal-Request-Id`, Bitcoin (txid/RBF discipline), Ethereum (nonce management + "did that tx actually revert?"), Monero (txid + proofs).
2. **Webhooks/events are the source of truth; the UI is a hint** — PSP webhooks (at-least-once, verify, dedupe, re-fetch) ≡ on-chain confirmations (wait for depth, handle reorgs, re-read state).
3. **Append-only ledger beats mutable columns** — double-entry ledger for fiat reconciliation ≡ the blockchain itself. Build the ledger at project start; retrofitting it is misery.
4. **Assume the adversarial input** — on-chain: anyone can call anything; off-chain: anyone can POST to your webhook endpoint or replay a request. Signature verification and state-machine discipline either side.

## 4. Sequenced study roadmap (≈8 serious weeks)

**Weeks 1–2 — foundations**: UTXO vs account models; PoW/PoS; keys, seeds, BIP-39/HD derivation; the payment lifecycle (auth/capture/settle/refund); PCI scope. *Build*: a regtest wallet flow with `bitcoin-cli`; a Stripe test-mode PaymentIntent end-to-end incl. webhook.
**Weeks 3–4 — crypto depth**: Ethereum EVM + gas + storage; write/compile/test a contract in Foundry; run the exploit list against toy contracts (reentrancy, oracle, access control); Lightning: open channels on signet, pay a BOLT11 invoice, resize via splicing on CLN. Monero: run `monerod` on stagenet, subaddress per counterparty, produce and verify a tx proof.
**Weeks 5–6 — fiat depth**: subscriptions with test clocks + dunning; a Connect Express pilot; tax engine integration; write the reconciliation job (Stripe balance transactions vs. your ledger). Read one PCI v4.0.1 SAQ end to end.
**Week 7 — cross-cutting**: GENIUS/MiCA/AMLR text-level reading; the v30/v31 Bitcoin release notes as governance case study; FCMP++ spec skimming; L2Beat stage model.
**Week 8 — capstone build** (one): a paid-API product accepting Stripe + stablecoins; or a self-custodial donation page (BTCPay-style on signet/testnets); or an escrow-style PSBT multisig tool.

## 5. Canonical documentation shelf

- **Bitcoin**: bips.dev · *Mastering Bitcoin 3e* · bitcoincore.org release notes · Bitcoin Optech archive · lightning-rfc (BOLTs) · BDK/LDK docs
- **Ethereum**: eips.ethereum.org · Solidity docs (+security page) · Foundry book · OpenZeppelin docs · ethereum.org/roadmap · Forkcast · L2Beat · SWC registry · RareSkills
- **Monero**: getmonero.org daemon/wallet RPC references · *Mastering Monero* · Monero Research Lab · `monero-oxide` FCMP++/CARROT repos · MAGIC Grants audit posts
- **PayPal**: developer.paypal.com (Orders v2, webhook verification, sandbox, PYUSD resource center) · Braintree dev docs · the official fee PDFs
- **Stripe**: docs.stripe.com (Payments lifecycle, webhooks, Connect, Billing, changelog) · stripe CLI · PCI SSC library
- **Regulation**: federalregister.gov (GENIUS NPRMs) · EUR-Lex (MiCA, AMLR 2024/1624) · FATF travel-rule guidance

*Every dated number in this pack will drift; the docs above are where you re-verify. The pack's own anchors are labeled "as of 16 Sep 2026" precisely so you know what to refresh first.*
