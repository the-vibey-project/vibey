---
name: money-monero
description: "Use when working with Monero — ring signatures, stealth addresses and RingCT, view keys, the FCMP++ upgrade and its real status, the 2025 Qubic hashrate episode, exchange delistings and how access actually works in 2026, and daemon/wallet RPC development. Companion to the other money-on-the-internet skills."
---

# Monero (XMR)

> **Part 4 of 7** of the *Money on the Internet* reference (plugin
> `money-on-the-internet`), covering §1–§7. Sibling skills:
> `money-start-here-and-the-five-systems` (how to read the pack, the five systems positioned side by side, learning paths),
> `money-bitcoin` (§1–§7 — UTXOs, policy vs consensus, wallets, Lightning, mining economics, Core development, the v30 fight),
> `money-ethereum` (§1–§5 — the account model, proof of stake, upgrades, using it, Solidity/Foundry/DeFi/security),
> `money-paypal` (§1–§6 — what it is, using it, the Sept 2026 US fee schedule, PYUSD, the APIs, PayPal vs Stripe),
> `money-stripe` (§1–§7 — the PaymentIntent model, integration patterns, compliance, pricing, the Bridge/Privy/Tempo stack),
> `money-choosing-a-rail-and-shared-patterns` (§1–§5 — the side-by-side, decision heuristics, the four transferable patterns, a study roadmap, the docs shelf),
> Section numbers are **per skill** here, not shared across the set: each chapter is a
> self-contained system. A reference written as §N → `skill` points at that skill's own §N.
>
> **Currency:** compiled 16 September 2026. The privacy stack in §2 is **[DURABLE]**. §3 (FCMP++) is **[VERSIONED — verify before relying]**, §4 (Qubic) is a **[CONTESTED]** interpretation with both positions shown, and §5 (access) moves with every delisting.
>
> **Not investment, legal, tax, or compliance advice.** The regulatory sections tell you what
> to ask your counsel, not what your obligations are.

> **⚠️ Privacy as a mandatory consensus rule, not an option — bought at the price of regulatory exclusion from most on-ramps.**
>
> **⚠️ GOTCHA** boxes and the pack's **[DURABLE]** / **[as of …]** / **[CONTESTED]** tags mark
> what is safe to learn once and what must be re-verified.
>
> **The three ideas that organize this document:**
> 1. **⚠️ THE GOAL IS FUNGIBILITY, NOT SECRECY**
>    **Every coin indistinguishable from every other, so none can carry a tainted history — a property transparent ledgers structurally lack. That is the engineering objective the whole privacy stack serves.**
> 2. **⚠️ MANDATORY PRIVACY MEANS NO ANONYMITY-SET FRAGMENTATION**
>    **Optional privacy splits users into those who used it and those who did not. Monero refuses that choice, which is why the protection is uniform and why it cannot be selectively disabled for a compliance regime.**
> 3. **⚠️ THE HARD PART IN 2026 IS ACCESS, NOT CRYPTOGRAPHY**
>    **The honest assessment includes the costs: delistings, on-ramp exclusion, and a contested 51%-style episode. §7 is [CONTESTED] by nature and says so.**

---

## 1. What it is — and the honest trade

Monero is a proof-of-work digital cash system with **privacy as a mandatory consensus rule, not an option**: senders, receivers and amounts are obscured *by default on every transaction*. The engineering goal is **fungibility** — every coin indistinguishable from every other, so no coin can carry a tainted history (a property transparent ledgers like Bitcoin's structurally lack).

The honest trade, stated up front: that same property has put Monero in a **shrinking regulatory perimeter**. Most large regulated exchanges have delisted it, an EU rule taking effect in 2027 bars regulated institutions from servicing it, and its small PoW security budget was publicly stress-tested in 2025. It is simultaneously the most technically serious privacy money and the most structurally embattled. Both halves are true; learn both.

---

## 2. The privacy stack — [DURABLE]

Every transaction uses all of these:

1. **Stealth addresses**: the sender derives a **one-time output address** from the recipient's published address; only the recipient's private **view key** can recognize funds as theirs. An outside observer cannot tell two payments went to the same person. Since *no address is ever reused on-chain*, the "address book" intuition from Bitcoin doesn't exist.
2. **Ring signatures**: each spent input is signed together with **15 decoy outputs pulled from the chain (ring size 16, since the Aug 2022 hard fork)**; the network verifies *one* output was spent without learning which.
3. **RingCT**: amounts are hidden in **Pedersen commitments**; the network verifies inputs + fee = outputs without seeing values.
4. **Bulletproofs+**: compact zero-knowledge range proofs proving committed amounts are non-negative (i.e., no value created from nothing) without revealing them.
5. **Subaddresses**: unlimited unlinkable receive addresses from one wallet seed. *(The older "integrated address" with payment IDs is deprecated — exchanges historically used it for deposit identification; don't build on it.)*
6. **Dandelion++**: transaction broadcast first propagates through a private "stem" phase over peers before flooding, making network-level IP↔tx linkage harder.
7. **RandomX**: a CPU-optimized PoW that keeps mining viable on commodity hardware and ASICs uneconomic — decentralization of *mining* by design.
8. **Dynamic block size + tail emission**: ~2-minute blocks that expand under demand, and after the subsidy curve ended (June 2022) a perpetual **0.6 XMR/block** keeps miners funded forever (~0.87%/yr effective inflation, declining).

The two-key model matters for development: **private view key** (sees incoming payments; shareable for watch-only/audit wallets) and **private spend key** (moves funds). For *outgoing* payments you can prove a specific payment was made with `get_tx_key`/`check_tx_proof` — selective disclosure is possible; the default is just that it's *optional*.

---

## 3. FCMP++: the upgrade that matters, and its real status — [VERSIONED, verify before relying]

**What it is**: replacing 16-decoy ring signatures with **Full-Chain Membership Proofs** — zero-knowledge proofs that an output is unspent and yours, over *the entire chain output set* (~100M+ outputs), built on Curve Trees with new Helios/Selene curves. Ships with **CARROT** (new backward-compatible addressing), forward secrecy, and outgoing view keys. Trade-offs: ~2.7 KB per input and heavier verification.

**Status as of 16 Sep 2026 — not on mainnet.** Mainnet still runs 16-member rings; latest releases are **CLI 0.18.5.1 "Fluorine Fermi" (8 Jul 2026)** and **GUI 0.18.5.2 (21 Jul 2026)**. FCMP++/CARROT live under the `v0.19.0.0-alpha` stressnet line:
- Public **beta stressnet launched 6 May 2026** (forked at block 2,997,100); earlier CARROT alpha stressnet 8 Jan 2026; `unlock_time` deprecation announced 10 May 2026 as prep ([CoinVast explainer](https://coinvast.io/articles/monero-fcmp-upgrade-explained)).
- Audits: **Veridise** (Apr–May 2025, circuit soundness); **Trail of Bits** integration review (May 2026); **ToB cryptography-implementation audit announced 17 Aug 2026 — 6 informational findings, zero high/medium/low, 5 resolved** ([MAGIC Grants](https://magicgrants.org/2026/08/17/Monero-FCMP-Cryptography-Implementation-ToB)).
- Active dev in `monero-oxide/monero-oxide` (fcmp++ branch) and the main repo (e.g. PR #10724 "curve tree builder" under milestone `fcmp++ hf`).
- **No committed mainnet fork date.** Outside estimates (not project commitments) run roughly **Nov 2026 – May 2027**, based on Monero's historical stressnet→mainnet cadence.
- ⚠️ **Widespread misreporting in 2026 claimed FCMP++ had already activated on mainnet** — that conflates the May stressnet with mainnet. Check the fork height on the daemon's `hard_fork_info` rather than the press.

---

## 4. The Qubic affair (Aug 2025) — what a "51% attack" actually looks like — [CONTESTED interpretation]

The timeline ([Cointelegraph](https://cointelegraph.com/news/monero-qubic-selfish-mining-51-percent-attack), [The Block](https://www.theblock.co/post/366535/monero-faces-chain-reorganization-fears-after-qubic-says-it-controls-51-of-hashrate), [Protos](https://protos.com/qubic-failed-to-51-attack-monero-but-dogecoin-is-next/), [DL News](https://www.dlnews.com/articles/defi/monero-hashrate-tug-war-ease-qubic-lose-51-percent-dominance/)):

- Qubic (Sergey Ivancheglo's L1) ran a months campaign paying miners **more than Monero's block reward** to mine XMR (funding it via QUBIC token buybacks) — an *economic* attack, not a technical one. Its hashrate share went <2% (May) → 25–45% (July).
- **11–12 Aug 2025**: Qubic claimed >50% and produced a **six-block-deep reorganization orphaning ~60 blocks**. XMR fell ~8–11%; Kraken, MEXC, HTX, WhiteBIT and swap services paused XMR moves (most resumed within days).
- **The dispute**: Ledger's CTO called it "a successful 51% attack"; Monero-side researchers and an analysis **commissioned by Qubic itself** (the "Minority Report," Shai Wyborski) estimated the real share at **28–35%**, achieved via **selfish mining** — withholding blocks to orphan rivals, which *simulates* majority dominance. No double-spends were found (BitMEX Research); Ivancheglo later joked it was a "**34% attack**." By 17 Aug the share had fallen back to ~35%. Qubic then pivoted to targeting Dogecoin.

**[DURABLE] lessons for any PoW builder/user**: (1) security budget = honest cost of attacking ≈ what honest miners earn; small PoW chains are attackable *by bribery*, not just by owned hardware; (2) selfish mining degrades a chain well below the 51% threshold — deep reorgs can happen at ~⅓ share; (3) "attacker got lucky with 30%" and "attacker has majority control" can look identical from outside; verify via orphan rate patterns, not press releases; (4) exchanges' defense-in-depth reaction (pausing deposits) is the correct operational response and your app should be built to tolerate it.

---

## 5. Using Monero in 2026 — access is the hard part

**Wallets**: official CLI/GUI, Feather (desktop power users), Cake/Monerujo/Edge (mobile). Full-node wallet = full privacy; remote-node or light-wallet use leaks varying metadata (the MyMonero-style "server scans for you with your view key" pattern trades privacy for speed). **[DURABLE] hygiene**: seed offline; subaddresses per counterparty; expect new receipts to be locked for **10 blocks (~20 min)** before spendable (mitigates reorg + decoy-poisoning issues).

**Where it trades as of mid/late 2026** ([delisting tracker](https://coinvast.io/articles/monero-delisting-tracker), [Kraken support](https://support.kraken.com/articles/support-for-monero-xmr-in-europe)):
- **Binance**: delisted globally Feb 2024 (leftovers force-converted to USDC). **Coinbase**: **never listed XMR** — the "Coinbase delisted Monero in April 2026" story circulating early this year is false; there was nothing to delist.
- **Kraken**: out of Ireland/Belgium June 2024, **out of the entire EEA 31 Oct 2024** — but **still lists XMR for US and other non-EEA users** (asset list current as of Aug 2026).
- Elsewhere: MEXC (deepest XMR/USDT books; no US users), KuCoin (now requires Level‑2 KYC for privacy-coin withdrawals), Gate.io, no-KYC venues like TradeOgre (thin liquidity); instant-swap services; **BTC↔XMR atomic swaps** via UnstoppableSwap/BasicSwap. ⚠️ **RetoSwap, the largest Haveno-based P2P venue, suspended trading in May 2026 after a ~$2.7M exploit** — P2P liquidity routes change fast; re-verify before directing anyone to one.
- Market context: despite everything above, XMR gained ~130% in 2025 and printed an **all-time high near $797 in Jan 2026**; ~73 exchanges had dropped at least one privacy coin by late 2025 (up from 51 in 2023). Liquidity migrated to non-custodial venues rather than vanishing. **LocalMonero's 2024 shutdown remains the biggest P2P gap.**

**Regulation, dated**: India FIU directed registered exchanges off XMR/ZEC/DASH on **25 Jan 2026** (Bybit fined ₹9.27 crore; the FIU clarified on 10 Mar 2026 that no *formal* ban existed — the delistings stuck anyway). In the EU, **AMLR (Reg. 2024/1624) Article 79 takes effect 10 Jul 2027**, barring regulated institutions from servicing anonymity-enhancing coins; MiCA's final CASP transition deadline passed 1 Jul 2026, pushing exits ahead of schedule. **Owning, self-custodying and P2P-transferring XMR remains legal** in these jurisdictions per the cited trackers; the restrictions target institutions. (Not legal advice — consult counsel for your jurisdiction.)

---

## 6. Developing on Monero

Monero dev ≠ Bitcoin dev. **There is no public address to watch, no script system, no tokens, no smart contracts.** Integration is daemon + wallet-RPC + proof machinery.

### The stack
- **`monerod`** — the daemon (P2P + consensus). RPC on port 18081: `get_info`, `get_block`, `send_raw_transaction`, fee estimates, `hard_fork_info`.
- **`monero-wallet-rpc`** — the wallet interface (JSON-RPC, port 18082): `create_wallet`, `get_address`, `make_integrated_address` (legacy), `create_account`/`create_address` (subaddresses), `transfer`, `transfer_split`, `get_balance`, `incoming_transfers`, `get_tx_key`, `check_tx_proof`, `sign`/`verify`, `export_view_key`, multisig RPCs.
- Libraries: **monero-cpp**, **monero-ts** (formerly monero-javascript — a full WASM wallet stack usable headless in Node), plus community Python/Go RPC wrappers.
- Networks: **mainnet / stagenet / testnet** — use stagenet for integration tests.
- Advanced: **BTC↔XMR atomic-swap protocol** (COMIT/UnstoppableSwap) — worth studying as the most production-real cross-chain primitive touching XMR; **M-of-N multisig** exists (threshold via multi-round key ceremony, no scripting).

### Canonical integration flows
```bash
# Watch-only audit wallet: view key + address, no spend key
monero-wallet-cli --generate-from-view-key audit.wallet

# Merchant-style receive: one subaddress per invoice
monero-wallet-rpc --daemon-address node.moneroworld.com:18089 ...
curl -X POST http://127.0.0.1:18082/json_rpc -d '{
  "jsonrpc":"2.0","id":"0","method":"create_address",
  "params":{"account_index":0,"label":"invoice-1042"}}'
# then poll incoming_transfers by subaddress_indices, enforce >=10 confs
```

```json
// Prove a payment was made (sender provides tx_key; recipient/checker verifies):
{"jsonrpc":"2.0","id":"0","method":"check_tx_proof",
 "params":{"txid":"…","address":"recipient-main-or-subaddress","signature":"InTxV1…/tx_key proof"}}
```

### Monero-dev gotchas
- ⚠️ **Balance scanning requires downloading and trial-decrypting every output with the view key** — "balance lookup by address" via a public explorer does not exist. Index your own incoming transfers; restore height matters (a wallet restored from seed only sees outputs after its creation unless you scan from genesis).
- **10-block output lock** and reorg handling: treat <10-conf receipts as provisional in application logic.
- **Payment proofs are per-tx and selective** — build your support flow around `get_tx_proof`/`check_tx_proof`, since no block explorer can adjudicate "did you pay me?"
- **Multisig is interactive and sessionful** (M-of-N rounds), unlike Bitcoin's script template; plan the UX accordingly.
- **Don't use `unlock_time`** for new logic — deprecated ahead of FCMP++ (May 2026 announcement).
- **Forward-compatibility**: after FCMP++, ring-size assumptions, decoy selection and some wallet-RPC internals change; CARROT addresses remain backward compatible, but keep RPC version pinning and test against the alpha stressnet if you maintain infrastructure.
- Mining: **RandomX is deliberately CPU-only economics** — a RandomX miner (XMRig) doubles as a stress tester; don't bother trying to GPU/ASIC it.

---

## 7. Assessment — [CONTESTED by nature]

*Strongest case*: the only major asset where fungibility is protocol-enforced; the FCMP++ arc shows research-grade engineering shipped through community funding (MAGIC Grants) with external audits; survived a publicly declared hashrate war with no double-spends; retained and even re-priced demand through coordinated delistings.
*Weakest case*: a shrinking regulated perimeter (EU AMLR 2027, India 2026), thin and KYC-increasing liquidity, a Qubic-scale security-budget scare, heavier UX than transparent chains, and zero programmability. Both are the same fact viewed from different threat models. Build your opinion from the sources, not from either tribe.

---

## Sources (as of 16 Sep 2026)

[CoinVast: FCMP++ explained](https://coinvast.io/articles/monero-fcmp-upgrade-explained) · [MAGIC Grants/ToB FCMP audit, 17 Aug 2026](https://magicgrants.org/2026/08/17/Monero-FCMP-Cryptography-Implementation-ToB) · [monero PR #10724](https://github.com/monero-project/monero/pull/10724) · [Cointelegraph: Qubic claims 51%](https://cointelegraph.com/news/monero-qubic-selfish-mining-51-percent-attack) · [The Block: reorg fears](https://www.theblock.co/post/366535/monero-faces-chain-reorganization-fears-after-qubic-says-it-controls-51-of-hashrate) · [Protos: "failed to 51%"](https://protos.com/qubic-failed-to-51-attack-monero-but-dogecoin-is-next/) · [DL News: hashrate eases](https://www.dlnews.com/articles/defi/monero-hashrate-tug-war-ease-qubic-lose-51-percent-dominance/) · [CoinVast delisting tracker](https://coinvast.io/articles/monero-delisting-tracker) · [Kraken EEA support page](https://support.kraken.com/articles/support-for-monero-xmr-in-europe) · [LeoDex post-delisting buying guide](https://leodex.io/learn/delistings/buy-monero-after-delistings)

Canonical study docs: *Mastering Monero* (free, SerHack), getmonero.org developer guides (daemon & wallet RPC references), the Monero Research Lab papers, and the FCMP++/CARROT spec repos under `monero-oxide`.
