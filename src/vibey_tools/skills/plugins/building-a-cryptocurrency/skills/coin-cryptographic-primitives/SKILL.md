---
name: coin-cryptographic-primitives
description: "Use when choosing a hash function, signature scheme, address format or key-derivation path for a chain, when building Merkle proofs or SPV inclusion checks, or when reviewing a nonce, seed-phrase or multisig design for hazards. Covers hash properties and current status, ECDSA against Schnorr, EdDSA and ring signatures, Merkle trees and the Merkle-Patricia trie, and BIP-32/39/44/380 key derivation. Part 2 of the Building a Cryptocurrency reference."
---

# Cryptographic Primitives

> **Part 2 of 8** of the *Building a Cryptocurrency* reference (plugin
> `building-a-cryptocurrency`), covering §2 — the hashes, signatures, key derivation and commitment schemes a chain is built from. Sibling skills:
> `coin-what-it-is-and-the-three-architectures` (§1 — the replicated-state-machine definition and the Bitcoin / Ethereum / Monero reference architectures),
> `coin-consensus-and-finality` (§3 — proof of work, proof of stake, Sybil resistance, fork choice and what finality actually means),
> `coin-building-a-utxo-chain` (§4 — the UTXO ledger model, script, transaction validation and what a fork of Bitcoin actually involves),
> `coin-building-an-account-chain` (§5 — the account/world-state model, the EVM, gas, and building a chain with smart contracts),
> `coin-privacy-features` (§6 — ring signatures, stealth addresses, confidential amounts and zero-knowledge approaches),
> `coin-networking-and-tokenomics` (§7–§8 — peer-to-peer gossip and propagation, then issuance, fees, supply schedules and incentive design),
> `coin-security-and-the-build-guide` (§9–§10 — what actually loses money, and the ordered guide to building and launching a chain),
>
> Section numbers are **shared across the whole set**: a reference written as §N → `skill` points
> into that sibling skill. This is an engineering reference, **not investment, legal or tax advice** —
> deploying a chain that handles real value carries securities, AML/KYC and consumer-protection
> obligations that are a question for counsel in your jurisdiction.

## §2 Cryptographic Primitives: The Building Blocks

**Scope and disclaimer, carried forward from the source document.** This is an engineering
reference, not investment advice. Creating a cryptocurrency is a legitimate software engineering
exercise with well-documented open-source reference implementations. However: deploying a
cryptocurrency that handles real value carries serious legal, financial, and security
responsibilities. Consult counsel regarding securities law, AML/KYC requirements, and consumer
protection regulations in your jurisdiction before launching anything that distributes tokens to
the public. §2 is where key material, addresses and seed phrases are defined, so it is directly
upstream of every custody and consumer-protection question.

Every cryptocurrency is built from the same cryptographic primitives. Understanding them deeply
is essential — not because you will implement them from scratch (you absolutely should not), but
because **every design decision in a cryptocurrency is ultimately a cryptographic decision**.

> **The golden rule of cryptography:** use vetted, well-maintained libraries at the highest level
> of abstraction that solves your problem. **Never implement primitives yourself.**

### 2.1 Hash functions

A hash function takes arbitrary input and produces a fixed-size output. The required properties:

| Property | What it means |
|---|---|
| Deterministic | The same input always gives the same output |
| Quick to compute | Cheap enough to run on every block, transaction and address |
| Preimage resistance | Infeasible to reverse — given the output, you cannot recover the input |
| Second preimage resistance | Infeasible to find a second input with the same output |
| Collision resistance | Infeasible to find *any* two inputs with the same output |

**Collision resistance is the weakest of these properties and the first to fall.** Design on the
assumption that it is the property you lose first.

In cryptocurrencies, hash functions serve three critical roles:

| Role | What it does | Reference practice |
|---|---|---|
| Block hashing | The proof-of-work puzzle and the chain linkage (§3 → `coin-consensus-and-finality`) | Bitcoin: SHA-256d (double SHA-256). Ethereum: Keccak-256 (a SHA-3 variant) |
| Merkle trees | Compact commitment to transaction sets (see 2.3) | Bitcoin: transaction sets per block. Ethereum: Merkle-Patricia trie over full state |
| Address derivation | Turning public keys into addresses | Bitcoin: RIPEMD-160(SHA-256(pubkey)). Ethereum: Keccak-256 |

#### Hash function status

| Function | Status | Verdict for a new chain |
|---|---|---|
| SHA-256 | Secure and well-studied | Natural choice |
| SHA-3 / Keccak-256 | Secure and well-studied | Natural choice |
| BLAKE2 / BLAKE3 | Faster alternatives with strong security properties | Viable |
| SHA-1 | **Broken for collisions**; deprecated everywhere that matters | Do not use for any security purpose |
| MD5 | **Completely broken** — collisions are trivial | Do not use for any security purpose |

#### Length extension attack

SHA-2 uses the Merkle-Damgård construction and is vulnerable to **length extension**: knowing
`H(m)` lets you compute `H(m + padding + extra)` without knowing `m`. This is why
`H(key + message)` is **not** a valid MAC construction. SHA-3 and BLAKE are not vulnerable to
this. For HMAC, the construction is specifically designed to resist length extension regardless of
the underlying hash.

### 2.2 Digital signatures

Digital signatures are the identity system of a cryptocurrency. You sign with your private key;
anyone can verify with your public key. The signature proves the holder of the private key
authorized the transaction, and the signature is **bound to the specific transaction data** — so it
cannot be replayed for a different transaction.

| Algorithm | Used By | Key Size | Notes |
|---|---|---|---|
| ECDSA (secp256k1) | Bitcoin (pre-Taproot), Ethereum | 256-bit | Widely deployed. Requires a per-signature random nonce `k` — reusing `k` across two signatures reveals the private key. This has broken real systems. |
| Schnorr (secp256k1) | Bitcoin (Taproot, Nov 2021) | 256-bit | Deterministic (no nonce hazard), linear and aggregatable (enabling MuSig2 multisig), provably secure under standard assumptions. The modern default for new designs. |
| EdDSA (Ed25519) | Many modern systems | 256-bit | Fast, deterministic, misuse-resistant. Curve25519 is designed to be hard to implement incorrectly. An excellent default for new cryptocurrencies. |
| Ring Signatures | Monero | 256-bit | A group of possible signers, but the actual signer is hidden among them. The key privacy primitive for anonymous transactions. |

Ring signatures are developed in full — ring size, decoy selection and the FCMP++ upgrade path —
in §6 → `coin-privacy-features`. Taproot address encoding and the script consequences of Schnorr
are in §4 → `coin-building-a-utxo-chain`.

> **THE ECDSA NONCE HAZARD**
>
> ECDSA requires a cryptographically random value `k` for each signature. If `k` is reused across
> two signatures with the same key, **simple algebra reveals the private key**. This has broken
> real systems, including a well-known game console. Even *biased* `k` (not perfectly random)
> leaks the key over many signatures. The solution: deterministic nonce generation (**RFC 6979**)
> or use Ed25519/Schnorr, which are deterministic by design. **If you use ECDSA, always use
> RFC 6979 deterministic nonces.**

### 2.3 Merkle trees

A Merkle tree is a binary tree of hashes where leaf nodes are hashes of data (transactions) and
each internal node is the hash of its children. The root hash is a compact cryptographic
commitment to the entire dataset. To prove a specific transaction is included in a block you
provide a **Merkle proof** — the sibling hashes along the path from the leaf to the root — which is
**O(log n)** in size. This enables lightweight clients (**SPV**) to verify transaction inclusion
without downloading the entire blockchain.

```
// Merkle tree construction (simplified)
leaves = [hash(tx1), hash(tx2), hash(tx3), hash(tx4)]
level1 = [hash(leaves[0] + leaves[1]), hash(leaves[2] + leaves[3])]
root   = hash(level1[0] + level1[1])

// To prove tx3 is included, provide:
// leaf = hash(tx3)
// sibling at level 0 = hash(tx4)
// sibling at level 1 = hash(leaves[0] + leaves[1])
// Verifier hashes up the tree and checks against the known root
```

| Chain | Structure | What the header commits to |
|---|---|---|
| Bitcoin | Merkle tree | Transaction sets within blocks |
| Ethereum | Merkle-Patricia trie | The entire state — accounts, balances, code, storage — not just the transactions |

Ethereum's trie commits the block header to the **full state**, which is what enables **state
proofs**; those are essential for light clients and bridges. The account/world-state model that
trie encodes is §5 → `coin-building-an-account-chain`.

### 2.4 Key generation, HD wallets, and seed phrases

Every user in a cryptocurrency has key pairs. **The private key is the identity**; the public key is
the address others send to. Key management is the hardest part of cryptocurrency — not the
cryptography, but the operational security around storing and using keys (the losses this causes
are §9–§10 → `coin-security-and-the-build-guide`).

| Standard | What it defines | What to watch |
|---|---|---|
| **BIP-39** seed phrases | A human-readable encoding of a master seed — 12–24 words from a defined wordlist | The seed is the backup of the entire wallet: **anyone with the seed has all the keys**. The optional passphrase is a plausible-deniability/decoy layer — and a loss vector, since losing it makes the wallet unrecoverable |
| **BIP-32** hierarchical-deterministic (HD) derivation | From the master seed, a tree of keys is deterministically derived; each branch produces a new key pair | Lets you never reuse addresses — **address reuse damages privacy permanently on transparent ledgers** |
| **BIP-44 / 49 / 84 / 86** | Standard derivation paths by script/address type | Pick paths deliberately; wallets interoperate on these |
| **Descriptors (BIP-380s)** | Strings such as `wpkh(xpub.../0/*)` that fully describe a wallet's script structure | The modern interchange format between wallet software and signing devices |

> **PRACTICAL KEY MANAGEMENT**
>
> For your cryptocurrency, you need to define:
> 1. **The key derivation scheme** — HD wallet with standard paths.
> 2. **The address format** — how public keys are encoded as addresses. Bitcoin uses Base58Check
>    or bech32; Ethereum uses hex with a checksum.
> 3. **The signature scheme and what exactly a signature commits to** — the sighash flags.
> 4. **The multi-signature support** — how M-of-N key sets are expressed in the transaction
>    format.

### 2.5 What §2 decides for the rest of the build

- Hash choice fixes the PoW puzzle and the chain linkage → §3 → `coin-consensus-and-finality`.
- Signature scheme and address format fix the script and address types → §4 → `coin-building-a-utxo-chain`.
- Merkle-Patricia state commitment is the precondition for state proofs → §5 → `coin-building-an-account-chain`.
- Ring signatures and hidden amounts are the privacy path → §6 → `coin-privacy-features`.
- Every one of these is a decision you make **once**, with vetted libraries, and never by writing
  the primitive yourself.
