---
id: skill-5-developing-on-ethereum-8b99c151b8
purpose: 5 developing on ethereum
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-ethereum/SKILL.md
requires: ["skill-4-using-ethereum-cec8448ef7"]
links: ["skill-sources-as-of-16-sep-2026-8abb461292"]
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
