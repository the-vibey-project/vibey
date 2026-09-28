---
id: skill-9-testing-f19c0c6124
purpose: 9 testing
source: src/vibey_tools/skills/plugins/cryptocurrency-development/skills/blockchain-security-testing-and-ops/SKILL.md
requires: []
links: ["skill-10-security-804287b292"]
---

## §9. Testing

### 9.1 The toolchain

**[VERSIONED] The Foundry/Hardhat choice is no longer binary, and the 2026 answer differs
from the 2022 answer.**

**Foundry** — Rust-based, **tests written in Solidity**, extremely fast, with built-in
fuzzing, invariant testing, mainnet forking, and cheatcodes (`vm.prank`, `vm.deal`,
`vm.expectRevert`, `vm.warp`). **The default for protocol and security-sensitive work.**

**Hardhat 3** — a major rewrite (new EDR engine, rebuilt config) that **added native
Solidity tests**, multichain/OP Stack simulation, and gas statistics. **This closed the two
historic gaps**: reported benchmarks put Hardhat 3 **within ~2× of Foundry on equivalent
test suites, versus the 10–20× penalty of Hardhat 2**, and Solidity-native testing removed
Foundry's exclusivity there.

**⚠️ The practical 2026 position: they coexist.** Foundry's `foundry.toml` is parsed by
Hardhat and artifacts can be shared, so many teams use **Foundry for fast unit/fuzz/
invariant testing of core logic and Hardhat for TypeScript integration tests, deployment
scripts, and L2 simulation**. **Pin a shared solc version across both** to avoid
compiler-version drift. The genuinely wrong move is choosing Hardhat in 2026 because a 2022
tutorial said so, then trying to retrofit Foundry-level test speed into a deeply
Hardhat-coupled codebase.

### 9.2 What to actually test

**[DURABLE] Unit tests are the floor, not the goal.** The techniques that find real bugs:

- **Fuzzing** — random inputs against properties. `forge test` does this natively; **turn it
  on for every function taking a numeric argument.**
- **Invariant / stateful fuzzing** — the highest-value technique available to most teams.
  Define properties that must hold across *any sequence* of calls ("total supply equals the
  sum of balances," "the vault is never insolvent," "no user can withdraw more than they
  deposited"), then let the fuzzer attack them. **Echidna** and **Medusa** are the
  specialist tools.
- **Fork testing** — run against real mainnet state and real dependencies. Catches
  integration assumptions that mocks hide.
- **Formal verification** — **Certora Prover**, **Halmos**, **Kontrol**, the SMTChecker.
  Mathematically proves properties hold under all inputs. **[VERSIONED] Increasingly a
  standard offering from security firms rather than an exotic add-on**, and it's the gold
  standard for high-value protocols.
- **Static analysis** — **Slither** (run it; it's fast and catches real things),
  **Mythril**, **Aderyn**.
- **Differential testing** against a reference implementation.
- **Coverage** — necessary, wildly insufficient. 100% line coverage tells you nothing about
  whether you tested the *adversarial* path.

---
