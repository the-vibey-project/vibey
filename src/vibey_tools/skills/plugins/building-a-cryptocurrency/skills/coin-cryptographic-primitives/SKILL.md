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
| Block hashing | The proof-of-work puzzle and the chain linkage (§3 → `coin-consensus-and-finality`) | Bitcoin: SHA-256d (double SHA-256). Ethereum: Keccak-256 (the pre-standardization Keccak variant, distinct from SHA3-256) |
| Merkle trees | Compact commitment to transaction sets (see 2.3) | Bitcoin: transaction sets per block. Ethereum: Merkle-Patricia trie over full state |
| Address derivation | Turning public keys into addresses | Bitcoin: RIPEMD-160(SHA-256(pubkey)). Ethereum: Keccak-256 |

#### Hash function status

| Function | Status | Verdict for a new chain |
|---|---|---|
| SHA-256 | Secure and well-studied | Natural choice |
| SHA3-256 (FIPS 202) | Secure and well-studied | Natural choice |
| Keccak-256 (the pre-standardization variant, Ethereum's) | Secure and well-studied, but **not** SHA3-256 — the padding and domain-separation rules differ, so the two return different digests for the same input | Natural choice, but pick it deliberately. Name which of the two your spec means and check which one your library's `sha3`/`keccak` entry point actually computes; getting this wrong silently breaks Ethereum compatibility |
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
authorized **the exact bytes that were signed** — and that is the whole of what it proves. It does
not make a transaction globally unique: the same signature over the same bytes verifies again,
later, and on any other chain that encodes transactions the same way.

**Replay resistance is a property of the ledger, not of the signature.** A UTXO chain gets it
because a transaction names the outputs it consumes and each output can only be consumed once
(§4 → `coin-building-a-utxo-chain`); an account chain gets it because the signed bytes include the
sender's nonce, which the state machine increments (§5 → `coin-building-an-account-chain`). Across
chains and contracts it takes explicit domain separation — a chain ID inside the signed bytes
(**EIP-155**), an **EIP-712** domain separator, or an equivalent tag. The rule for a new design:
whatever must not be replayable has to be inside the bytes you sign.

| Algorithm | Used By | Key Size | Notes |
|---|---|---|---|
| ECDSA (secp256k1) | Bitcoin (pre-Taproot), Ethereum | 256-bit | Widely deployed. Requires a per-signature random nonce `k` — reusing `k` across two signatures reveals the private key. This has broken real systems. |
| Schnorr (secp256k1) | Bitcoin (Taproot, Nov 2021) | 256-bit | Linear and aggregatable (enabling MuSig2 multisig); BIP340 specifies deterministic nonce derivation, but nonce handling remains security-critical. The modern default for new designs. |
| EdDSA (Ed25519) | Many modern systems | 256-bit | Fast, and hard to misuse: **RFC 8032** derives the per-signature nonce by hashing the private key's prefix together with the message, so no per-signature RNG sits in the path to fail. That is the *derivation* doing the work — a repeated nonce still reveals the key. Ed25519 signs over **edwards25519**, a twisted Edwards curve; **Curve25519** is the birationally equivalent Montgomery curve used by **X25519 key exchange**, which is a different primitive and does not sign. Do not substitute one for the other. Verification strictness (cofactor handling, signature malleability) differs between libraries, so a consensus system must pin one rule and test against it. An excellent default for new cryptocurrencies. |
| Ring Signatures | Monero | 256-bit | A group of possible signers, but the actual signer is hidden among them. The key privacy primitive for anonymous transactions. |

Ring signatures are developed in full — ring size, decoy selection and the FCMP++ upgrade path —
in §6 → `coin-privacy-features`. Taproot address encoding and the script consequences of Schnorr
are in §4 → `coin-building-a-utxo-chain`.

> **THE NONCE HAZARD, AND WHY IT IS NOT ONLY ECDSA'S**
>
> ECDSA requires a secret per-signature value `k`. If `k` is reused across two signatures with the
> same key, **simple algebra reveals the private key**. This has broken real systems, including a
> well-known game console. Even *biased* `k` (not perfectly random) leaks the key over many
> signatures.
>
> The fix is a **specified deterministic derivation**: **RFC 6979** for ECDSA, **BIP340** for
> Schnorr, **RFC 8032** for Ed25519. Be precise about what that buys. Determinism is a property of
> the derivation a specification chose, **not of the signature scheme**: Schnorr and Ed25519 are
> nonce-based too, and a repeated or biased nonce reveals the key there by the same algebra. They
> are safer because their standard derivation takes the random-number generator out of the path,
> not because the hazard is absent.
>
> **Whichever scheme you use, use its specified derivation and never a homegrown one.** One
> exception to keep in view: interactive multi-party signing (**MuSig2**, **FROST**) needs a fresh
> nonce per signing session that is never reused across sessions or retries — single-signer
> deterministic derivation does not carry over, and reusing a session nonce leaks the key share.

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
