---
id: skill-4-the-evm-d7618d8d17
purpose: 4 the evm
source: src/vibey_tools/skills/plugins/cryptocurrency-development/skills/blockchain-smart-contract-development/SKILL.md
requires: []
links: ["skill-5-solidity-and-the-contract-languages-3b618ce5a9"]
---

## §4. The EVM

### 4.1 The execution model

**[DURABLE]** A **stack machine** (1024-deep, 256-bit words) with four data locations, and
understanding the distinction between them is the single most load-bearing piece of EVM
knowledge:

| Location | Persistence | Cost | Notes |
|---|---|---|---|
| **Stack** | Transient | Cheapest | 1024 slots, 256-bit words |
| **Memory** | Per-call | Cheap, **expands quadratically** | Byte-addressed scratch space |
| **Storage** | **Permanent, on-chain** | **Very expensive** | 256-bit → 256-bit map per contract |
| **Calldata** | Read-only input | Cheap to read | Cheaper than memory for large read-only args |
| **Transient storage** (EIP-1153) | Cleared at end of tx | Cheap | `TSTORE`/`TLOAD` — reentrancy guards, callbacks |

**[DURABLE] Storage dominates gas cost.** A cold `SLOAD` is ~2100 gas, a zero→nonzero
`SSTORE` is ~20,000, and a nonzero→nonzero write ~2900 (with refunds for clearing).
**Almost all gas optimization is really storage-access optimization**, and everything else
is noise by comparison.

**Call types**: `CALL` (new context, `msg.sender` = caller), **`DELEGATECALL`** (⚠️
**executes target code in the caller's storage context** — the basis of proxies (§6.1)
and of some of the worst bugs in the field's history), `STATICCALL` (read-only, reverts on
state change), and `CREATE`/`CREATE2` (the latter gives deterministic addresses from a
salt, enabling counterfactual deployment).

**Reverts** unwind all state changes in the frame and refund remaining gas. **[DURABLE]
The atomicity of a transaction is your most powerful safety property** — if any part
reverts, none of it happened. Design around it.

### 4.2 Gas

```
tx cost = 21,000 base
        + calldata (4 gas/zero byte, 16/non-zero)
        + execution opcodes
        + storage (dominant)
  fee   = gas_used × (base_fee + priority_fee)   [EIP-1559; base fee is BURNED]
```
**⚠️ Gas is a security parameter, not just a cost.** Unbounded loops over user-controlled
arrays are a **denial-of-service vulnerability** — if the array grows past the block gas
limit, the function becomes permanently uncallable, potentially locking funds forever.

**The 63/64 rule** (EIP-150): a call forwards at most 63/64 of remaining gas, so the caller
always retains enough to handle the return. **⚠️ This makes "gas griefing" possible** — a
callee can deliberately consume its allocation to make the caller fail.

### 4.3 EVM-compatible vs. EVM-equivalent

**[DURABLE] The distinction matters when porting.** "EVM-compatible" chains may differ in
opcode behaviour, gas costs, precompiles, block time assumptions, and `block.timestamp`
semantics. **"EVM-equivalent"** claims byte-for-byte identical execution. **⚠️ Never assume
a contract audited on mainnet is safe on another EVM chain without re-review** — different
gas schedules alone can turn safe code into a DoS.

---
