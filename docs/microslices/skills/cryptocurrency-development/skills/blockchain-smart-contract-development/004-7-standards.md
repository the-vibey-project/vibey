---
id: skill-7-standards-c0759fdcf2
purpose: 7 standards
source: src/vibey_tools/skills/plugins/cryptocurrency-development/skills/blockchain-smart-contract-development/SKILL.md
requires: ["skill-6-contract-architecture-6e0a379add"]
links: ["skill-8-defi-primitives-and-mev-1b32e4d00f"]
---

## §7. Standards

### 7.1 Tokens

| Standard | What |
|---|---|
| **ERC-20** | Fungible tokens. ⚠️ See below |
| **ERC-721** | NFTs. `safeTransferFrom` invokes a receiver hook — **a reentrancy vector** |
| **ERC-1155** | Multi-token, batch operations |
| **ERC-4626** | Tokenized vaults. ⚠️ **Inflation/donation attacks on the first depositor** are the classic bug — mitigate with virtual shares or a dead-shares seed |
| **ERC-2612** | `permit` — gasless approvals via signature |
| **ERC-777** | ⚠️ Hooks caused real reentrancy exploits. **Largely deprecated in practice** |

> **⚠️ GOTCHA — ERC-20 is a standard that many tokens don't follow, and assuming compliance
> is how integrations break:**
> - **Non-standard return values** — USDT and others don't return a bool. **Use
>   OpenZeppelin's `SafeERC20`.**
> - **Fee-on-transfer tokens** — the amount received ≠ the amount sent. **Measure balance
>   before and after**, don't trust the argument.
> - **Rebasing tokens** — balances change without transfers.
> - **Non-18 decimals** — USDC has 6. Hardcoding 18 is a recurring, expensive bug.
> - **Blocklists** — USDC/USDT can freeze addresses, so a transfer can revert forever.
> - **Approval race** — some tokens require setting the allowance to 0 before changing it.
> - **Malicious tokens** — if you let anyone list a token, you've let them run arbitrary
>   code inside your callstack.

### 7.2 The rest

**ERC-165** (interface detection), **EIP-712** (typed structured signing — what makes
signature prompts human-readable; ⚠️ **always include a domain separator with `chainId` and
the verifying contract, or your signature is replayable across chains and contracts**),
**ERC-1271** (contract signature validation — necessary for smart accounts),
**ERC-7201** (namespaced storage layout, §6.1).

### 7.3 Account abstraction

**[VERSIONED] The most consequential UX change in years, and it landed in two pieces.**
**ERC-4337** implements smart accounts entirely outside the protocol — UserOperations,
a Bundler, an EntryPoint, and Paymasters (which enable sponsored gas and paying fees in
ERC-20). **EIP-7702** (shipped in **Pectra, May 2025**) went further by letting a regular
EOA temporarily execute as a smart contract, so **existing wallets** gain batching, session
keys, sponsored gas, and social recovery **without migrating to a new address**.

**⚠️ EIP-7702 is a live security consideration, not just a feature.** An EOA delegating to
malicious code is a new and effective drainer pattern, and wallet and contract code that
assumes "`msg.sender` with no code is a plain EOA" is now making an unsafe assumption.

---
