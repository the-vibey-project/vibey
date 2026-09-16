---
name: money-ethereum
description: "Use when working with Ethereum — the account and world-state model, the EVM, proof of stake and the two-process node, the upgrade timeline, gas and transaction types, Solidity and Foundry, contract security and the access-control losses that dominate 2026 incident data, DeFi primitives, L2s and MEV. Companion to the other money-on-the-internet skills."
---

# Ethereum

> **Part 3 of 7** of the *Money on the Internet* reference (plugin
> `money-on-the-internet`), covering §1–§5. Sibling skills:
> `money-start-here-and-the-five-systems` (how to read the pack, the five systems positioned side by side, learning paths),
> `money-bitcoin` (§1–§7 — UTXOs, policy vs consensus, wallets, Lightning, mining economics, Core development, the v30 fight),
> `money-monero` (§1–§7 — the privacy stack, FCMP++, the Qubic affair, access and delistings, daemon/wallet development),
> `money-paypal` (§1–§6 — what it is, using it, the Sept 2026 US fee schedule, PYUSD, the APIs, PayPal vs Stripe),
> `money-stripe` (§1–§7 — the PaymentIntent model, integration patterns, compliance, pricing, the Bridge/Privy/Tempo stack),
> `money-choosing-a-rail-and-shared-patterns` (§1–§5 — the side-by-side, decision heuristics, the four transferable patterns, a study roadmap, the docs shelf),
> Section numbers are **per skill** here, not shared across the set: each chapter is a
> self-contained system. A reference written as §N → `skill` points at that skill's own §N.
>
> **Currency:** compiled 16 September 2026. The EVM model, storage layout, gas semantics and the security canon are **[DURABLE]**. §3 (upgrades) is heavily dated and should be re-verified before it is relied on.
>
> **Not investment, legal, tax, or compliance advice.** The regulatory sections tell you what
> to ask your counsel, not what your obligations are.

> **⚠️ Bitcoin's ledger idea generalized into a replicated state machine whose state includes executable code.**
>
> **⚠️ GOTCHA** boxes and the pack's **[DURABLE]** / **[as of …]** / **[CONTESTED]** tags mark
> what is safe to learn once and what must be re-verified.
>
> **The three ideas that organize this document:**
> 1. **⚠️ EVERY FULL NODE RE-EXECUTES EVERY TRANSACTION**
>    **That single constraint explains gas, the storage layout, why computation is expensive and data is worse, and why L2s exist at all.**
> 2. **⚠️ ACCESS CONTROL IS WHERE THE MONEY IS ACTUALLY LOST**
>    **Not reentrancy, not exotic math — the 2026 loss data says privileged functions with wrong or missing guards. Audit the modifiers before the arithmetic.**
> 3. **⚠️ A CONTRACT IS PUBLIC, IMMUTABLE, AND ADVERSARIALLY EXERCISED FROM BLOCK ONE**
>    **Upgradeability is a design decision with its own attack surface, not a safety net, and checks-effects-interactions is a habit rather than a rule you remember under pressure.**

---

## 1. The mental model

Ethereum is Bitcoin's ledger idea generalized into a **world computer**: a replicated state machine where the state includes **accounts with executable code**. Where Bitcoin stores UTXOs, Ethereum stores an **account tree** — externally owned accounts (EOAs, controlled by keys) and **contract accounts** (controlled by their own code). A transaction is either a value transfer or a function call into a contract; every full node re-executes every transaction and must reach the same resulting state.

Three consequences:
- **Composability**: contracts call contracts within a single atomic transaction. This powers DeFi — and means your protocol's safety depends on code you don't control.
- **Everything is public and adversarial**: every function is callable by anyone, in any order, by attackers who read your source. There is no "hidden" on-chain.
- **Bugs are irreversible money losses**; there is no support line. (For reversibility, see PayPal/Stripe — that's the trade.)

**As of 16 Sep 2026**, ETH trades near **$2,400–2,500**, vs an ATH of **$4,953 (24 Aug 2025)**; the Sept 15–16 drawdown tracked Bitcoin's on the failed CLARITY cloture vote ([Economic Times](https://economictimes.indiatimes.com/markets/cryptocurrency/crypto-news/bitcoin-trades-near-75000-as-clarity-act-setback-weighs-fed-decision-in-focus/articleshow/134285423.cms)). Spot ETH ETFs exist (they saw ~$141M outflows on Sept 15).

---

## 2. Proof of stake and the two-process node — [DURABLE]

Since **The Merge (Sept 2022)**, Ethereum runs **Gasper**: the **LMD-GHOST** fork choice + **Casper FFG** finality. Blocks arrive every 12 seconds (slots); 32 slots make an epoch; a checkpoint finalizes after two epochs (~13 min) once 2/3 of staked ETH attests. **Slashing** destroys stake for provable equivocation; **inactivity leaks** bleed offline validators during non-finality. Validators stake 32 ETH; **EIP-7251 (Pectra, May 2025)** raised the effective max to 2,048 ETH to allow consolidation.

**Running a node = running two processes**: a **consensus client** (Lighthouse, Prysm, Teku, Nimbus, Lodestar, Grandine) and an **execution client** (Geth, Nethermind, Reth, Besu, Erigon, ethrex), joined by the Engine API. ⚠️ **Client diversity is a systemic risk**: >1/3 of stake on one client can halt finality; >2/3 could finalize an *invalid* chain. This is not theoretical — **Reth suffered a network-wide outage on 2 Sept 2025** processing a specific block; multi-client operators stayed up. As of Aug 2026 verification, EL diversity had genuinely improved (Geth ~36–41% by various measures, Nethermind ~23–32%, Reth ~14–15%) — ⚠️ sources disagree substantially because they measure different populations; one 2026 staking survey put Nethermind ~45% among stakers. **If you stake, run a minority client.**

---

## 3. Upgrades: what's shipped, what's next — heavily dated

| Fork | Date | Headline |
|---|---|---|
| Merge | Sep 2022 | PoW→PoS; ~99.95% energy cut |
| Shapella | Apr 2023 | staking withdrawals |
| Dencun | Mar 2024 | **EIP-4844 blobs** — L2 data costs fell ~90% |
| Pectra | May 2025 | **EIP-7702** (EOAs can execute as smart accounts), EIP-7251 |
| **Fusaka** | **3 Dec 2025** | **PeerDAS** — validators *sample* blob data instead of downloading it all; gas limit ~60M |
| **Glamsterdam** | **targeted Q4 2026 — not confirmed** | ePBS (EIP-7732), **Block-Level Access Lists (EIP-7928)** for parallel execution, state gas repricing (EIP-8037/8038), faster validator exits (EIP-8061), cheaper basic transfers (EIP-2780) |
| Hegotá | 2027 | FOCIL headlining; Verkle discussed |

**Glamsterdam status as of 16 Sep 2026** ([ethereum.org roadmap](https://ethereum.org/roadmap/glamsterdam/), [crypto.news](https://crypto.news/ethereum-targets-oct-6-for-glamsterdam-on-sepolia/)):
- **Sepolia testnet tentatively 6 Oct 2026 (epoch 351232)** — set at ACDC #186 *before* any stable devnet run; Lido and Optimism have asked for a full day of devnet stability plus cross-client fixes first.
- Devnet-8 exposed a consensus bug; devnet-9 had a finality failure; **devnet-11 ran 14 Sept** as the gating test; persistent public devnet "Platåberget" live since Aug.
- **No mainnet date exists.** December 2026 is discussed, aspirational, and entirely test-dependent. Anything claiming a firm date is guessing.
- ⚠️ Numbering churn is real: Aug 2026 materials referenced the state-gas repricing as EIP-7904; current roadmap material uses EIP-8037/8038. When EIPs get renumbered or split pre-fork, that itself is normal process — check [Forkcast](https://forkcast.org) / ethereum.org before writing code against a number.

**Why Glamsterdam matters to builders** ([DURABLE-ish]): BALs declare a block's state reads *before* execution → parallel transaction execution; ePBS brings proposer-builder separation **in-protocol** (today it runs through out-of-protocol MEV-Boost relays — a live centralization dependency) and propagating payloads get ~9s instead of ~2s.

### The fee environment changed — update your priors

If "ETH mainnet is too expensive" was formed in 2021–2023, it's stale. **Mid-September 2026: daily average gas 0.68–0.97 gwei, utilization ~45–56%, average tx fee ~0.0001 ETH (~$0.25); simple transfers at snapshot time cost $0.003–0.006** ([YCharts gas series](https://ycharts.com/indicators/ethereum_average_gas_price), [Etherscan gas tracker](https://etherscan.io/gasTracker)). Do the math for your workload — but do it against current numbers, not folklore.

---

## 4. Using Ethereum

- **Wallets**: EOAs (MetaMask, Rabby, hardware) and **smart accounts** (Safe, ERC-4337 accounts). Since Pectra's **EIP-7702**, an ordinary EOA can temporarily execute as smart-contract code — giving *existing* wallets batching, session keys, sponsored gas, and social recovery without address migration. ⚠️ **7702 is also a drainer vector**: an EOA delegating to malicious code is now a standard phishing payload; never sign a delegation you don't understand, and note that "no code at `msg.sender` ⇒ plain EOA" is no longer a safe assumption in contract logic.
- **L2s are where the activity is**: optimistic rollups (OP Stack, Arbitrum — ~7-day withdrawal windows unless fast-exit) vs. ZK/validity rollups (proof-verified exits in minutes) vs. validiums (cheaper, weaker data availability). **[DURABLE] The only three security questions about any L2**: who can censor you, who can steal from you, and can you exit without permission? **L2Beat's stage classification** answers them honestly; the escape hatch to verify is **forced inclusion via L1**. Most rollups still run a **centralized sequencer** (censorship/liveness SPOF) — decentralized sequencing remains largely unshipped.
- **Bridges are the most-exploited category in crypto history** — lock-and-mint honey pots, and verification of foreign-chain state. Ask of any bridge: *who attests the source-chain event?* A 5-of-9 multisig bridge has the security of a 5-of-9 multisig. A 2026 example: forged Axelar messages passed a receiver contract missing access control → ~$3M drained. Prefer canonical/L1-verified or light-client bridges for size.
- **DeFi essentials**: AMMs (`x·y=k` constant product; concentrated liquidity; LPs bear impermanent loss), over-collateralized lending with liquidation incentives, fiat-backed vs crypto-backed vs algorithmic stablecoins (the last has a long failure history), liquid staking. Oracles: **never read a DEX spot price on-chain as "the price"** — a flash loan moves it in one transaction; use Chainlink/Pyth/RedStone feeds or meaningful TWAPs, and check feed staleness and L2 sequencer uptime.

---

## 5. Developing on Ethereum

### 5.1 The EVM in one screen — [DURABLE]

Stack machine, 256-bit words, 1024-deep stack. Four data locations: **stack** (transient), **memory** (per-call, quadratically-priced expansion), **storage** (permanent, the expensive one: cold `SLOAD` ≈ 2,100 gas; zero→nonzero `SSTORE` ≈ 20,000), **calldata** (read-only input), plus **transient storage** (EIP-1153: `TSTORE`/`TLOAD`, cleared at tx end — modern reentrancy guards). **Almost all gas optimization is storage-access optimization.**

Calls: `CALL` (fresh context), **`DELEGATECALL` (executes target code in *your* storage context — the basis of proxies and of some of the worst bugs in history)**, `STATICCALL`, `CREATE`/`CREATE2` (deterministic addresses/counterfactual deployment). **Reverts unwind everything in the frame** — transaction atomicity is your strongest safety tool; design around it.

Fees: `gas_used × (base_fee + priority_fee)`, EIP‑1559 — base fee is **burned**. ⚠️ Gas is a security parameter: **unbounded loops over user-controlled arrays are permanent DoS** (function becomes uncallable past the block gas limit; funds can be stuck forever). The 63/64 rule (EIP-150) enables gas griefing by callees.

"EVM-compatible" ≠ "EVM-equivalent": opcode semantics, gas schedules, precompiles and `block.timestamp` behavior differ per chain. **Never assume a contract safe on mainnet is safe on another EVM chain.**

### 5.2 Solidity, pinned and current

- **Latest stable: 0.8.37, released 10 Sept 2026** — a bugfix release: `delete` on a memory byte array cleared 32 bytes instead of one (all ≤0.8.36, evmasm pipeline); spill-slot collision in mutual recursion under `--via-ir` (0.7.2–0.8.36); Amsterdam EVM support (`block.slotnum`, EIP-7843) ([release announcement](https://www.soliditylang.org/blog/2026/09/10/solidity-0.8.37-release-announcement/)).
- **[DURABLE]** Since 0.8.0, arithmetic overflow **reverts by default** — eliminating a whole bug class (and meaning anything still on 0.6/0.7 is a live risk; a 2026 exploit hit a five-year-old 0.6.10 contract for exactly this).
- **Pin the compiler exactly** (`pragma solidity 0.8.37;`), never floating; record optimizer settings; prefer custom `error`s over revert strings; know `receive()` vs `fallback()`; **never authorize on `tx.origin`**; use `viaIR` deliberately and re-test (it changes codegen).

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

contract Vault {
    error Unauthorized();
    event Deposit(address indexed from, uint256 amount);
    mapping(address => uint256) public balanceOf;

    function withdraw(uint256 amount) external {
        uint256 bal = balanceOf[msg.sender];
        if (bal < amount) revert Unauthorized();
        balanceOf[msg.sender] = bal - amount;      // effects BEFORE interaction (CEI)
        (bool ok, ) = msg.sender.call{value: amount}("");
        if (!ok) revert Unauthorized();
    }
}
```

### 5.3 Toolchain (2026 position)

**Foundry** (Rust; tests in Solidity; fuzzing, invariant testing, mainnet forking, cheatcodes) is the default for protocol/security work. **Hardhat 3** (rewrite: EDR engine, native Solidity tests, multichain sim) closed the old 10–20× speed gap to ~2×. **They coexist**: many teams run Foundry for unit/fuzz/invariant and Hardhat for TS integration/deployment (Hardhat even parses `foundry.toml`). Choosing one because a 2022 tutorial said so is the failure mode.

**The testing ladder, in escalating value**:
1. Unit tests — the floor, not the goal.
2. **Fuzzing** every numeric input (`forge test` native).
3. **Invariant/stateful fuzzing** — define properties ("vault never insolvent") and let **Echidna/Medusa** attack call sequences. Highest-value technique available to most teams.
4. **Fork testing** against real mainnet state — mocks hide integration assumptions.
5. **Formal verification** — Certora, Halmos, Kontrol, SMTChecker; now a standard offering for high-value protocols.
6. **Static analysis** — Slither (run it; fast; catches real things), Mythril, Aderyn.
Coverage is necessary and wildly insufficient: 100% line coverage says nothing about adversarial paths.

```solidity
// Foundry invariant example: the fuzzer tries to break solvency with any call sequence
function invariant_vaultSolvent() public view {
    assertGe(address(vault).balance, vault.totalOwed());
}
```

### 5.4 Architecture decisions that cost money when wrong

- **Upgradeability [CONTESTED]**: the strongest argument *for* is unfixable bugs; *against*, you've reintroduced trust behind an **upgrade key that is now your #1 target**. Patterns: transparent proxy, **UUPS** (upgrade logic in the implementation — brickable if you deploy one without it), beacon, diamond (EIP-2535, contested), or **immutable (safest, least forgiving)**. The recurring proxy failures: **storage layout collisions** (append-only across upgrades; use ERC-7201 namespaced storage), **uninitialized implementations** (`_disableInitializers()`), constructors not running in proxy context, and `immutable` state living in code, not proxy storage. **Minimum standard for anything holding value: multisig (Safe) + timelock on the upgrade path.**
- **Access control is the top loss category — by far.** From the OWASP Smart Contract Top 10 for 2026 (149 incidents, ~$1.42B in 2025): **access control ≈ $953M** vs logic errors $64M, reentrancy $36M, flash-loan exploits $34M. Use `Ownable2Step` or `AccessControl`; audit *every* privileged path including initializers and upgrades.
- **Checks-Effects-Interactions** (validate → update state → external calls) prevents most reentrancy; add `nonReentrant` or transient-storage guards; watch *cross-function* and *read-only* reentrancy (view functions returning stale mid-tx state to an oracle consumer). **Pull over push** for payouts.
- **ERC-20 integration gotchas [DURABLE]**: non-standard returns (USDT) → use `SafeERC20`; fee-on-transfer → measure balance delta, never trust the argument; rebasing tokens; **non-18 decimals** (USDC=6); blocklists can freeze transfers; approval race (set 0 first); **letting users list arbitrary tokens = letting them run code in your callstack**. ERC-4626 vaults: the first-depositor share-inflation attack — mitigate with virtual shares/dead shares. EIP-712 signed messages: always include domain separator with `chainId` + verifying contract, else your signature replays elsewhere.
- **ERC-4337 / EIP-7702 account abstraction**: bundlers + EntryPoint + paymasters (sponsored gas, fees in ERC‑20) — the UX baseline for serious consumer apps in 2026.

### 5.5 What actually loses money now — read this twice

Hardened contracts pushed exploit losses down ~89% YoY in Q1 2026 (DefiLlama) — **and total losses didn't drop, because attackers moved to the humans**: ~$306M of ~$450M lost in Q1 2026 across 145 incidents was phishing/social engineering; one January attack drained **$282M without touching code**; six audited protocols were breached, **one after 18 prior audits**. Chainalysis attributes ~76% of 2026 hack value to state-backed actors (Lazarus-style): months-long social engineering, operatives embedded as IT staff. **Operational consequence**: audits are necessary and radically insufficient; key management, opsec, insider risk, and signing hygiene (no blind signing; human-readable prompts) now deserve first-class budget. **Verify contract source on the explorer** — Chainalysis documented ~$36.7M lost across five protocols via their own *unverified* contracts in six months.

### 5.6 Ops checklist (before mainnet)

Audited + findings resolved · testnet-exercised · exact compiler+optimizer pinned · reproducible build · **source verified on explorer** · ownership to multisig/timelock (never an EOA) · initializers locked · pause mechanism tested · monitoring live (Forta/Defender) · incident runbook written. For indexers: events are your API (emit generously), handle **reorgs** (indexed data can un-happen), prefer The Graph/Ponder/Subsquid or a careful `eth_getLogs` pipeline. Frontend: **viem + wagmi** standard, RainbowKit/ConnectKit, WalletConnect; JSON-RPC essentials: `eth_call`, `eth_estimateGas`, `eth_sendRawTransaction`, `eth_getLogs` (rate-limited — the usual indexer bottleneck), `debug_traceTransaction` (archive/debug nodes; your best debugging tool). **Own node vs provider (Alchemy/Infura/QuickNode) is a real architectural decision**: providers trade away censorship-resistance and rate-limit freedom for operational simplicity. NVMe is non-negotiable for self-hosting; archive nodes are very large.

---

## Sources (as of 16 Sep 2026)

[ethereum.org Glamsterdam roadmap](https://ethereum.org/roadmap/glamsterdam/) · [crypto.news: Sepolia target](https://crypto.news/ethereum-targets-oct-6-for-glamsterdam-on-sepolia/) · [Solidity 0.8.37 announcement](https://www.soliditylang.org/blog/2026/09/10/solidity-0.8.37-release-announcement/) · [YCharts avg gas price](https://ycharts.com/indicators/ethereum_average_gas_price) · [Etherscan gas tracker](https://etherscan.io/gasTracker) · ETH price: [Economic Times, 16 Sep 2026](https://economictimes.indiatimes.com/markets/cryptocurrency/crypto-news/bitcoin-trades-near-75000-as-clarity-act-setback-weighs-fed-decision-in-focus/articleshow/134285423.cms). Durable mechanics, client-diversity figures, fork history through Fusaka, and the 2026 security-loss data per the `cryptocurrency-development` reference set, verified Aug 2026.

Canonical study docs: the Ethereum execution/consensus specs, EIPs (eips.ethereum.org), the Foundry book, the Solidity docs + security considerations page, OpenZeppelin Contracts docs, the Smart Contract Weakness Classification registry (SWC), L2Beat, and the RareSkills blog for deep mechanics.
