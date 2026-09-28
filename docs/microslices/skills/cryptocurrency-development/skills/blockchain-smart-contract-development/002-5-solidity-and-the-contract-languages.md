---
id: skill-5-solidity-and-the-contract-languages-3b618ce5a9
purpose: 5 solidity and the contract languages
source: src/vibey_tools/skills/plugins/cryptocurrency-development/skills/blockchain-smart-contract-development/SKILL.md
requires: ["skill-4-the-evm-d7618d8d17"]
links: ["skill-6-contract-architecture-6e0a379add"]
---

## §5. Solidity and the Contract Languages

### 5.1 Solidity

**[VERSIONED] The 0.8.x line is current** — **0.8.36 (July 2026)** was the latest stable at
the time of writing, with 0.8.37 in nightly development. Releases are frequent and often
carry security fixes; **0.8.36 alone included two medium-severity security fixes.**

**[DURABLE] Pin an exact compiler version in production.** Use `pragma solidity 0.8.30;`
rather than `^0.8.0`. Floating pragmas mean your deployed bytecode depends on whoever
compiled it, which breaks reproducible builds and verification.

**What 0.8 changed and why it matters**: **arithmetic overflow and underflow revert by
default** since 0.8.0. This eliminated an entire vulnerability class — and it's why
**contracts still running on 0.6.x and 0.7.x are a live risk**. One 2026 exploit hit a
contract on **Solidity 0.6.10, which lacks automatic overflow protection**, after nearly
five years deployed. `unchecked { }` opts out where you've proven safety and want the gas.

**The essentials**:
```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

contract Example {
    // visibility: external | public | internal | private  — always explicit
    // state mutability: pure | view | payable | (default)
    // storage vs memory vs calldata — declare deliberately

    error InsufficientBalance(uint256 available, uint256 required); // custom errors:
                                                                    // cheaper than strings
    event Transfer(address indexed from, address indexed to, uint256 value);
        // `indexed` → topics, filterable by log queries; max 3 indexed params

    modifier onlyOwner() { if (msg.sender != owner) revert Unauthorized(); _; }

    receive() external payable {}   // plain ETH transfers
    fallback() external payable {}  // unmatched calldata
}
```
**⚠️ `msg.sender` vs `tx.origin`**: **never use `tx.origin` for authorization.** It's the
original EOA, so any contract the user calls can relay a call to you and pass the check.
This is a textbook phishing vector.

**`viaIR`** (the IR-based codegen pipeline) produces better optimization and is increasingly
the default in serious projects; enable it deliberately and re-test, since it changes
generated code. **Yul** is the intermediate language, and **inline assembly** drops to it —
use sparingly, and know that **assembly bypasses Solidity's safety checks entirely**.

### 5.2 The alternatives

**Vyper** — deliberately restricted, Python-like, no inheritance, no inline assembly,
bounded loops. **[CONTESTED]** Its restrictions are a real security argument; against it,
a smaller ecosystem and its own compiler-bug history (a Vyper reentrancy-guard compiler bug
caused a major 2023 exploit — **the compiler is part of your trust surface**).
**Huff / Yul** — near-assembly, for extreme gas optimization. Very high risk.
**Fe**, **Sway** (FuelVM), **Cairo** (Starknet), **Move** (Aptos/Sui — resource-oriented,
with a genuinely different and interesting ownership model), **Rust** (Solana, CosmWasm,
NEAR).

---
