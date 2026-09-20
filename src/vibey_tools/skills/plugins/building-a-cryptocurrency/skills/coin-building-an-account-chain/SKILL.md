---
name: coin-building-an-account-chain
description: "Use when deciding between shipping an ERC-20 token, a new account-model chain, or an L2 rollup, and when designing or reviewing account state, EVM data locations, gas budgets, call semantics, or a fungible token contract. Covers the account world-state model, the EVM stack machine and its storage costs, the EIP-1559 gas system, the ERC-20 interface and its integration hazards. Part 5 of the Building a Cryptocurrency reference."
---

# Building an Ethereum-Style Account Coin

> **Part 5 of 8** of the *Building a Cryptocurrency* reference (plugin
> `building-a-cryptocurrency`), covering §5 — the account/world-state model, the EVM, gas, and building a chain with smart contracts. Sibling skills:
> `coin-what-it-is-and-the-three-architectures` (§1 — the replicated-state-machine definition and the Bitcoin / Ethereum / Monero reference architectures),
> `coin-cryptographic-primitives` (§2 — the hashes, signatures, key derivation and commitment schemes a chain is built from),
> `coin-consensus-and-finality` (§3 — proof of work, proof of stake, Sybil resistance, fork choice and what finality actually means),
> `coin-building-a-utxo-chain` (§4 — the UTXO ledger model, script, transaction validation and what a fork of Bitcoin actually involves),
> `coin-privacy-features` (§6 — ring signatures, stealth addresses, confidential amounts and zero-knowledge approaches),
> `coin-networking-and-tokenomics` (§7–§8 — peer-to-peer gossip and propagation, then issuance, fees, supply schedules and incentive design),
> `coin-security-and-the-build-guide` (§9–§10 — what actually loses money, and the ordered guide to building and launching a chain),
>
> Section numbers are **shared across the whole set**: a reference written as §N → `skill` points
> into that sibling skill. This is an engineering reference, **not investment, legal or tax advice** —
> deploying a chain that handles real value carries securities, AML/KYC and consumer-protection
> obligations that are a question for counsel in your jurisdiction.

## §5 Building an Ethereum-Style Coin (Account + PoS + EVM)

> **SCOPE AND DISCLAIMER** (carried forward from the document opening, because this part covers
> deploying and distributing a token). This is an engineering reference, not investment advice.
> Creating a cryptocurrency is a legitimate software engineering exercise with well-documented
> open-source reference implementations. However: deploying a cryptocurrency that handles real
> value carries serious legal, financial, and security responsibilities. Consult counsel regarding
> securities law, AML/KYC requirements, and consumer protection regulations in your jurisdiction
> before launching anything that distributes tokens to the public.

If you want to create something similar to Ethereum — a cryptocurrency with smart contract
capability — the architecture is **fundamentally different from Bitcoin**. The ledger is
account-based, the consensus can be PoS (§3 → `coin-consensus-and-finality`), and the state
includes executable code.

### 5.1 The account model

Instead of UTXOs (§4 → `coin-building-a-utxo-chain`), the state is a mapping of addresses to
accounts. There are two types:

- **Externally owned accounts (EOAs)** — controlled by private keys.
- **Contract accounts** — controlled by their code.

Each account has a balance, a **nonce** (transaction count, preventing replay), and for contract
accounts, stored code and storage. A transaction is either a value transfer (EOA to EOA) or a
function call into a contract. **Every full node re-executes every transaction and must reach the
same resulting state.**

```
// Account state (stored in the Merkle-Patricia trie)
Account {
  nonce: 42,                    // number of transactions sent from this ac
  balance: 1000000000000000000, // in wei (1 ETH = 10^18 wei)
  storageRoot: "0x...",         // root of the account's storage trie (cont
  codeHash: "0x..."             // hash of the contract bytecode (contracts
}
```

*(Source note: the trailing comments are cut off at the right margin in the source document and
are reproduced as they appear.)*

> **WHY ACCOUNTS INSTEAD OF UTXO?**
> The account model enables **persistent state**, which is what makes smart contracts possible.
> A contract has a persistent balance and storage that any transaction can read and modify. In a
> UTXO model, "state" must be encoded in the spending conditions of outputs, which is far more
> limited. The trade-off: every node must re-execute every transaction (because state changes
> depend on the current state, which depends on all prior transactions), **which is why gas
> exists** — to limit computation per block and make denial-of-service expensive.

### 5.2 The Ethereum Virtual Machine (EVM)

The EVM is a **stack machine with 256-bit words and a 1024-deep stack**. It has four data
locations, and understanding the distinction between them is the single most important piece of
EVM knowledge:

| Location | Persistence | Cost | Notes |
|---|---|---|---|
| Stack | Transient (within execution) | Cheapest | 1024 slots, 256-bit words |
| Memory | Per-call (cleared after call) | Cheap, expands quadratically | Byte-addressed scratch space |
| Storage | Permanent, on-chain | Very expensive | 256-bit key to 256-bit value map, per contract |
| Calldata | Read-only input | Cheap to read | Cheaper than memory for large read-only data |
| Transient storage (EIP-1153) | Cleared at end of transaction | Cheap | Modern reentrancy guards, callbacks |

*(Source note: the prose says "four data locations"; the table as printed carries five rows, the
fifth being EIP-1153 transient storage. Both are reproduced as they appear.)*

**Storage dominates gas cost.** A cold storage read (`SLOAD`) costs **~2100 gas**. A storage write
from zero to non-zero (`SSTORE`) costs **~20,000 gas**. Almost all gas optimization is really
storage-access optimization, and everything else is noise by comparison.

**Call types:**

| Opcode | Semantics |
|---|---|
| `CALL` | New context; the callee sees the calling address as `msg.sender` |
| `DELEGATECALL` | Executes target code in the caller's storage context and preserves the caller's `msg.sender` and `msg.value` — the basis of upgradeable proxies and of some of the worst bugs in history |
| `STATICCALL` | Read-only, reverts on state change |
| `CREATE` / `CREATE2` | Deploy new contracts; `CREATE2` gives deterministic addresses from a salt |

**Reverts:** if any part of a transaction reverts, **all state changes are unwound**. This
atomicity is your most powerful safety property — design around it.

### 5.3 The gas system

```
Transaction cost = 21,000 base
                 + calldata (4 gas/zero byte, 16/non-zero)
                 + execution opcodes
                 + storage access (dominant)

Fee = gas_used × (base_fee + priority_fee)    [EIP-1559]
// base_fee is BURNED, priority_fee goes to the block proposer
```

Gas is **not just a cost — it is a security parameter**. Unbounded loops over user-controlled
arrays are a denial-of-service vulnerability: if the array grows past the block gas limit, the
function becomes **permanently uncallable, potentially locking funds forever**. Every loop must be
bounded. (Fee-market design and the burn are covered in §7–§8 →
`coin-networking-and-tokenomics`.)

### 5.4 The ERC-20 token standard

If your goal is to create a **token** (rather than an entire new blockchain), the ERC-20 standard
on Ethereum (or any EVM-compatible chain) is the established path. An ERC-20 token is a smart
contract that implements a standard interface for fungible tokens:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable2Step.sol";

contract MyCoin is ERC20, Ownable2Step {
    // Constructor mints the initial supply to the deployer
    // 1,000,000 tokens with 18 decimals (the Ethereum standard)
    constructor() ERC20("MyCoin", "MYC") Ownable(msg.sender) {
        _mint(msg.sender, 1_000_000 * 10**18);
    }

    // Owner can mint more (or remove this for fixed supply)
    function mint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
    }
}
```

The ERC-20 interface requires: `totalSupply()`, `balanceOf(address)`,
`transfer(address, uint256)`, `approve(address, uint256)`,
`transferFrom(address, address, uint256)`, `allowance(address, address)`, plus the `Transfer` and
`Approval` events.

> **ERC-20 INTEGRATION GOTCHAS**
> Many ERC-20 tokens do not follow the standard exactly: **USDT does not return a bool on
> `transfer`** (use OpenZeppelin's `SafeERC20` wrapper), **some tokens charge fees on transfer**
> (measure balance before and after, do not trust the argument), **some use non-18 decimals**
> (USDC has 6), and **some can freeze addresses** (USDC/USDT blocklists). If your contract
> integrates with arbitrary ERC-20 tokens, handle all of these — and remember that letting users
> list arbitrary tokens means **letting them run arbitrary code in your callstack**.

### 5.5 Creating a token vs. creating a blockchain

These are fundamentally different undertakings.

| | Creating an ERC-20 token | Creating a new blockchain |
|---|---|---|
| Scope | Deploying a smart contract — maybe 100 lines of Solidity | A multi-year effort |
| Cost | A few hundred dollars of deployment gas | Custom node implementation, consensus mechanism, P2P network, wallet software, block explorers, exchange listings, and a community of validators or miners |
| Ecosystem | Immediate compatibility with the entire Ethereum ecosystem (wallets, exchanges, DeFi, indexers) | Bootstrapped from scratch |

The right choice depends on your goals:

| Choose | If |
|---|---|
| **A token** (ERC-20 or equivalent) | You want a fungible digital asset, you need it to interoperate with existing DeFi, you do not need custom consensus rules, and you want to launch quickly |
| **A new blockchain** | You need custom consensus (different privacy guarantees, different validator model, different economics), you need custom transaction semantics, you need scale that L2s cannot provide, or you need independence from another chain's governance and fee market |
| **An L2 rollup** | You want your own execution environment and fee market, but want to inherit the security of an L1 (Ethereum, Bitcoin, etc.). **OP Stack, Arbitrum Orbit, ZK Stack, and Polygon CDK** are the established paths — they give you a custom chain without bootstrapping security from scratch |

### 5.6 Where this connects

- **Hashes, Keccak-256, Merkle-Patricia commitments, key derivation** → §2 → `coin-cryptographic-primitives`
- **PoS, Gasper, slashing, explicit finality for the chain under an account model** → §3 → `coin-consensus-and-finality`
- **The UTXO alternative this part is defined against** → §4 → `coin-building-a-utxo-chain`
- **Privacy, which an account model does not give you** → §6 → `coin-privacy-features`
- **Gossip, mempool, fee markets, issuance and distribution of the token you just minted** → §7–§8 → `coin-networking-and-tokenomics`
- **Access control, reentrancy, `DELEGATECALL` proxy bugs, and the ordered build-and-launch guide** → §9–§10 → `coin-security-and-the-build-guide`
- **The three reference architectures and the five key design decisions that led you here** → §1 → `coin-what-it-is-and-the-three-architectures`
