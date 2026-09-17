---
name: coin-building-a-utxo-chain
description: "Use when designing or implementing a UTXO-based chain, modelling transaction inputs and outputs, writing or auditing Bitcoin Script locking and unlocking scripts, deciding which address formats a wallet or node must support, or forking Bitcoin. Covers the UTXO ledger model, block structure and chain linkage, the coinbase transaction and its maturity rule, Script validation, and the four Bitcoin address types. Part 4 of 8 of the Building a Cryptocurrency reference."
---

# Building a Bitcoin-Style UTXO Coin

> **Part 4 of 8** of the *Building a Cryptocurrency* reference (plugin
> `building-a-cryptocurrency`), covering §4 — the UTXO ledger model, script, transaction validation and what a fork of Bitcoin actually involves. Sibling skills:
> `coin-what-it-is-and-the-three-architectures` (§1 — the replicated-state-machine definition and the Bitcoin / Ethereum / Monero reference architectures),
> `coin-cryptographic-primitives` (§2 — the hashes, signatures, key derivation and commitment schemes a chain is built from),
> `coin-consensus-and-finality` (§3 — proof of work, proof of stake, Sybil resistance, fork choice and what finality actually means),
> `coin-building-an-account-chain` (§5 — the account/world-state model, the EVM, gas, and building a chain with smart contracts),
> `coin-privacy-features` (§6 — ring signatures, stealth addresses, confidential amounts and zero-knowledge approaches),
> `coin-networking-and-tokenomics` (§7–§8 — peer-to-peer gossip and propagation, then issuance, fees, supply schedules and incentive design),
> `coin-security-and-the-build-guide` (§9–§10 — what actually loses money, and the ordered guide to building and launching a chain),
>
> Section numbers are **shared across the whole set**: a reference written as §N → `skill` points
> into that sibling skill. This is an engineering reference, **not investment, legal or tax advice** —
> deploying a chain that handles real value carries securities, AML/KYC and consumer-protection
> obligations that are a question for counsel in your jurisdiction.

## §4 Building a Bitcoin-Style Coin (UTXO + PoW + Script)

If you want to create something similar to Bitcoin, this is the architecture you need to build.
It is **the most proven design** — Bitcoin has run continuously since **January 2009**, processing
trillions of dollars in value with **zero downtime and no protocol-level hacks**.

> **SCOPE AND DISCLAIMER (carried forward from the front of the reference).** This is an
> engineering reference, not investment advice. Creating a cryptocurrency is a legitimate
> software engineering exercise with well-documented open-source reference implementations.
> However: deploying a cryptocurrency that handles real value carries serious legal, financial
> and security responsibilities. **Consult counsel regarding securities law, AML/KYC
> requirements, and consumer protection regulations in your jurisdiction before launching
> anything that distributes tokens to the public.**

The three decisions this architecture fixes — UTXO ledger, Proof of Work, limited non-Turing-complete
script — are the first three of the five key design decisions in §1 → `coin-what-it-is-and-the-three-architectures`.
The PoW half is covered in §3 → `coin-consensus-and-finality`; the account-model alternative is §5 →
`coin-building-an-account-chain`.

### The UTXO model

**There are no account balances in a UTXO system.** The ledger is a set of *unspent transaction
outputs* (UTXOs), each locked by a small program (a script). A "balance" is the **sum of UTXOs your
keys can unlock**.

- A transaction **consumes existing UTXOs as inputs** and **creates new UTXOs as outputs**.
- **Every input must be fully consumed** — you cannot spend part of a UTXO.
- To send 5 coins from a 10-coin UTXO, the transaction consumes the 10-coin UTXO and produces
  **two outputs**: 5 to the recipient and 5 back to yourself as **change**.

```
// Transaction structure (simplified)
Transaction {
  inputs: [
    {
      prev_txid: "abc123...",     // reference to the transaction that crea
      output_index: 0,            // which output of that transaction
      scriptSig: <...>, // proves you can spend this UTXO
      sequence: 0xFFFFFFFF        // used for relative timelocks
    }
  ],
  outputs: [
    {
      value: 500000000,           // in satoshis (smallest unit)
      scriptPubKey: <...>  // locks this output for the recipient
    },
    {
      value: 499999000,           // change back to sender
      scriptPubKey: <...>
    }
  ],
  locktime: 0                     // absolute timelock
}
```

*Note on the listing above:* the source is text extracted from a PDF. Angle-bracketed placeholders
(shown here as `<...>`) and the right-hand ends of two comments were lost in extraction; the values,
field names and structure are reproduced exactly as the source gives them.

**Values are in satoshis, the smallest unit.** The two outputs shown, `500000000` and `499999000`,
are the recipient output and the change output of a single spend.

#### WHY UTXO?

The UTXO model has **three key advantages**:

1. **Parallelizability** — transactions that do not touch the same UTXOs can be validated
   independently, enabling parallel transaction processing.
2. **Simpler verification** — a node only needs to track the set of unspent outputs, not the full
   balance of every account.
3. **Privacy** — since there are no persistent accounts, coin selection and change generation create
   natural mixing.

**The disadvantage: no persistent state**, which makes smart contracts much harder. You need
extensions such as Bitcoin's **covenants** or Cardano's **eUTXO** model.

### Block structure and chain linkage

```
Block {
  header: {
    version: 1,
    prev_block_hash: "000000...",    // links to previous block — this is w
    merkle_root: "abcdef...",        // root of the Merkle tree of transact
    timestamp: 1697000000,           // Unix timestamp
    bits: 0x1d00ffff,                // encoded difficulty target
    nonce: 2083236893                // the value miners grind to find a va
  },
  transactions: [coinbase_tx, tx1, tx2, ...]
}
```

| Header field | Value in the listing | Role |
|---|---|---|
| `version` | `1` | Block version |
| `prev_block_hash` | `"000000..."` | Links to the previous block — the chain linkage |
| `merkle_root` | `"abcdef..."` | Root of the Merkle tree of the block's transactions |
| `timestamp` | `1697000000` | Unix timestamp |
| `bits` | `0x1d00ffff` | Encoded difficulty target |
| `nonce` | `2083236893` | The value miners grind to find a valid block |

*The Role column restates the listing's own comments; three of them (`prev_block_hash`,
`merkle_root`, `nonce`) were cut off mid-word by the PDF extraction and are completed here.*

**The coinbase transaction.** The **first transaction in every block** is the coinbase transaction.
It **has no inputs** and **creates new coins from nothing** — the block subsidy plus fees. This is
**the only way new coins enter circulation**. Its outputs become new UTXOs that can be spent only
after a **maturity period of 100 blocks in Bitcoin**, ensuring they are deeply buried before becoming
spendable.

**Why the chain is immutable.** Each block's header contains the hash of the previous block's header.
Changing any transaction in a historical block changes its Merkle root → changes its header hash →
breaks the link from the next block — requiring the attacker to **redo all the work for every
subsequent block**.

### Bitcoin Script — the locking/unlocking language

Bitcoin Script is **stack-based** and **intentionally not Turing-complete (no loops)**.

- Each **output** carries a **locking script** (`scriptPubKey`).
- Each **input** provides an **unlocking script** (`scriptSig`).
- To validate, the node **concatenates `scriptSig` + `scriptPubKey` and executes**. If the result is
  **true**, the spend is valid.

```
// Pay-to-Public-Key-Hash (P2PKH) — the most common Bitcoin script
// Locking script (scriptPubKey):
OP_DUP OP_HASH160 <...> OP_EQUALVERIFY OP_CHECKSIG

// Unlocking script (scriptSig):
<...> <...>

// Execution:
<...> <...> OP_DUP OP_HASH160 <...> OP_EQUALVERIFY OP_CHECKSIG
// 1. Duplicate pubkey
// 2. Hash it
// 3. Compare with the expected hash
// 4. Verify the signature against the pubkey
// Result: true or false
```

*Same extraction caveat:* the `<...>` markers stand where angle-bracketed operands appeared in the
source PDF and were stripped in extraction. The opcode sequence and the four execution steps are
reproduced exactly.

**From this small vocabulary, everything is built:**

| Construct | Mechanism |
|---|---|
| **Multisig** | M-of-N signatures required |
| **Absolute timelock** | `OP_CHECKLOCKTIMEVERIFY` |
| **Relative timelock** | `OP_CHECKSEQUENCEVERIFY` (and the input `sequence` field) |
| **HTLCs** | Hash-time-locked contracts, for payment channels and atomic swaps |
| **Taproot MAST** | Merkleized Abstract Syntax Tree — commits to multiple possible spending conditions in a Merkle tree, **revealing only the one actually used** |

### Address types you need to support

| Type | Prefix | Script | Example |
|---|---|---|---|
| Legacy P2PKH | `1` | Pay to public key hash | `1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa` |
| P2SH (nested SegWit) | `3` | Pay to script hash | `3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy` |
| Bech32 SegWit v0 | `bc1q` | Pay to witness public key hash | `bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq` |
| Bech32m Taproot v1 | `bc1p` | Pay to taproot | `bc1p5d7rj7q...` (Schnorr signatures) |

All four are on the list a Bitcoin-style wallet or node **needs to support**. The hash and signature
primitives behind them — including Schnorr for Taproot — are in §2 → `coin-cryptographic-primitives`.

### Where the rest of this design lives

| Question this part leaves open | Go to |
|---|---|
| PoW difficulty, fork choice, how many confirmations count as final | §3 → `coin-consensus-and-finality` |
| Persistent state and smart contracts (the account alternative) | §5 → `coin-building-an-account-chain` |
| Hiding sender, receiver and amount on a UTXO chain | §6 → `coin-privacy-features` |
| Block and transaction propagation between peers | §7–§8 → `coin-networking-and-tokenomics` |
| Block subsidy schedule, fees, and what pays for security long-term | §7–§8 → `coin-networking-and-tokenomics` |
| What actually loses money, and the ordered build-and-launch guide | §9–§10 → `coin-security-and-the-build-guide` |
