# Money on the Internet Plugin

Five systems that move money — **Bitcoin, Ethereum, Monero, PayPal, Stripe** — positioned
against each other and then taken one at a time: what each actually is, how to use it, and what
"developing on it" means. Protocol mechanics and wallet engineering on the chain side; the
payment lifecycle, fee schedules, compliance scope and API surface on the fiat side; and a
decision guide for picking between them.

One reference, split into 7 skills — one per system, plus a start-here and a decision guide —
so a task loads only the part it needs.

**The framing that organizes the whole set:**

- On the crypto side, **deployed code or a held key is money in public**. There is no
  chargeback and nobody to call. Failure modes: theft, loss, protocol risk.
- On the fiat side, **money is data with a counterparty and a regulator**. There *is* someone
  to call — and that someone can freeze you, reverse you, and hold 90-day reserves. Failure
  modes: idempotency bugs, webhook mishandling, reconciliation drift, account risk.
- Monero sits deliberately at the far end of the crypto side: fungibility and privacy bought at
  the price of regulatory exclusion from most regulated on-ramps.

Reference, not tutorial. Every claim carries a durability tag: **[DURABLE]** mechanics that do
not expire (UTXO vs account models, EVM storage layout, idempotency keys,
checks-effects-interactions), **[as of …]** claims that will (a fee schedule, a fork date, a
client version — each with a link so you can re-verify), and **[CONTESTED]** where sources
genuinely disagree, with both positions shown. Where a search found nothing, that is stated
rather than padded out with plausible-sounding reconstruction. Section numbers are **per skill**,
not shared: each chapter is a self-contained system.

**This is an engineering and usage guide. It is not investment, legal, tax, or compliance
advice** — the regulatory sections tell you what to ask your counsel, not what your obligations
are.

## Skills

- **money-start-here-and-the-five-systems** — How the pack was built and how to trust it; the
  five systems positioned on what they are, native asset, who can censor or reverse, finality,
  programmability, privacy and headline cost; learning paths by what you actually want to do.
- **money-bitcoin** (§1–§7) — ⚠️ There are no balances, only UTXOs; protocol mechanics that
  matter; using Bitcoin well; the Lightning Network; 2026 mining economics; developing on
  Bitcoin; ⚠️ the v30 governance fight **[CONTESTED]**.
- **money-ethereum** (§1–§5) — The world-computer mental model; proof of stake and the
  two-process node **[DURABLE]**; upgrades shipped and next (heavily dated); using Ethereum;
  ⚠️ developing on Ethereum — Solidity, Foundry, the security canon, DeFi, MEV.
- **money-monero** (§1–§7) — What it is and the honest trade; ⚠️ the privacy stack
  **[DURABLE]**; FCMP++ **[VERSIONED]**; the Qubic affair **[CONTESTED]**; ⚠️ access as the
  hard part; developing on Monero; assessment.
- **money-paypal** (§1–§6) — What it actually is; using it; ⚠️ the US fee schedule effective
  1 Sept 2026; PYUSD and the 2026 strategy **[VERSIONED]**; developing on PayPal; PayPal vs.
  Stripe vs. both.
- **money-stripe** (§1–§7) — What it actually is; ⚠️ core API mechanics **[DURABLE]**;
  integration patterns from easiest to most control; compliance reality; money-movement
  products and pricing; the Bridge–Privy–Tempo stablecoin stack **[VERSIONED]**; the
  regulatory backdrop.
- **money-choosing-a-rail-and-shared-patterns** (§1–§5) — The side-by-side; decision
  heuristics; ⚠️ the four engineering patterns that transfer everywhere; a sequenced study
  roadmap; the canonical documentation shelf.

## Related plugins

This is a **systems** reference — what these five rails are, and how to choose between them.
Two neighbours cover the same ground as **disciplines**:

- `cryptocurrency-development` — blockchain engineering at the protocol and application layers,
  independent of any one chain.
- `ecommerce-development` — commerce and payments systems: the payment lifecycle, integration
  engineering, PSPs and gateways, payment methods and rails.

Reach for those when the question is "how do I build this kind of thing"; reach for this one
when the question is "which of these should I use, and what is it actually doing".
