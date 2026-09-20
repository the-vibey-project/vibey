---
name: coin-privacy-features
description: "Use when adding sender, receiver or amount privacy to a chain, choosing among ring signatures, stealth addresses and confidential transactions, sizing an anonymity set, planning a move to full-chain membership proofs, or weighing mandatory privacy against exchange delisting and EU AMLR exposure. Covers the Monero reference design end to end: stealth address derivation and view-key scanning, ring size 16, Pedersen commitments with Bulletproofs+ range proofs, FCMP++, Dandelion++, subaddresses and RandomX. Part 6 of 8 of the Building a Cryptocurrency reference."
---

# Privacy Features

> **Part 6 of 8** of the *Building a Cryptocurrency* reference (plugin
> `building-a-cryptocurrency`), covering §6 — ring signatures, stealth addresses, confidential amounts and zero-knowledge approaches. Sibling skills:
> `coin-what-it-is-and-the-three-architectures` (§1 — the replicated-state-machine definition and the Bitcoin / Ethereum / Monero reference architectures),
> `coin-cryptographic-primitives` (§2 — the hashes, signatures, key derivation and commitment schemes a chain is built from),
> `coin-consensus-and-finality` (§3 — proof of work, proof of stake, Sybil resistance, fork choice and what finality actually means),
> `coin-building-a-utxo-chain` (§4 — the UTXO ledger model, script, transaction validation and what a fork of Bitcoin actually involves),
> `coin-building-an-account-chain` (§5 — the account/world-state model, the EVM, gas, and building a chain with smart contracts),
> `coin-networking-and-tokenomics` (§7–§8 — peer-to-peer gossip and propagation, then issuance, fees, supply schedules and incentive design),
> `coin-security-and-the-build-guide` (§9–§10 — what actually loses money, and the ordered guide to building and launching a chain),
>
> Section numbers are **shared across the whole set**: a reference written as §N → `skill` points
> into that sibling skill. This is an engineering reference, **not investment, legal or tax advice** —
> deploying a chain that handles real value carries securities, AML/KYC and consumer-protection
> obligations that are a question for counsel in your jurisdiction.

## §6 Privacy Features: Building Toward Monero

> **SCOPE AND DISCLAIMER (carried from the front of the reference).** This is an engineering
> reference, not investment advice. Creating a cryptocurrency is a legitimate software engineering
> exercise with well-documented open-source reference implementations. However: deploying a
> cryptocurrency that handles real value carries serious legal, financial, and security
> responsibilities. Consult counsel regarding securities law, AML/KYC requirements, and consumer
> protection regulations in your jurisdiction before launching anything that distributes tokens to
> the public. This section in particular ends in live regulation — read the privacy trade-off below
> before committing to mandatory privacy.

If you want your cryptocurrency to have privacy — where sender, receiver, and amount are hidden —
the **Monero architecture is the reference implementation**.

**Privacy is not a feature you bolt on; it is a design decision that pervades every layer of the
protocol.** Treat it as a ledger-model commitment (§4 → `coin-building-a-utxo-chain`), a consensus
commitment (§3 → `coin-consensus-and-finality`), and a networking commitment (§7 →
`coin-networking-and-tokenomics`) simultaneously, not as a wallet feature.

### The three things that must be hidden

Each of the three properties needs its own mechanism. None substitutes for another.

| Hidden property | Mechanism | Verification / recognition | Principal cost |
|---|---|---|---|
| **Receiver** | Stealth addresses — a one-time output address derived from the published address | Only the recipient private view key can recognize the funds as theirs | Wallet must trial-decrypt every output on the chain |
| **Sender** | Ring signatures — the real input signed together with decoys pulled from the chain | Network verifies one of the outputs was spent, but cannot tell which | Anonymity set limited to the ring size (currently 16) |
| **Amount** | Confidential transactions — Pedersen commitments | Network verifies inputs + fee = outputs without seeing the actual values | Range proofs required for every committed amount |

### Stealth addresses — hidden receivers

The sender derives a **one-time output address** from the recipient's published address. Only the
recipient's **private view key** can recognize funds as theirs. An outside observer cannot tell that
two payments went to the same person. **Since no address is ever reused on-chain, there is no
"address book" to analyze.**

Mechanically:

1. The recipient publishes a public address, which encodes **two public keys — a spend key and a
   view key**.
2. The sender generates a **random ephemeral private key**.
3. The sender computes a **shared secret using ECDH with the recipient's view key**.
4. The sender derives a **one-time public key** for the output from that shared secret.
5. The recipient **scans every output on the chain**, tries to decrypt each one with their view key,
   and recognizes their outputs when the derivation matches.

This is **computationally expensive** — the wallet must trial-decrypt every output on the chain —
**but it is the foundation of receiver privacy**. Budget for it in wallet design: scan cost grows
with the whole chain's output set, not with the user's own activity.

### Ring signatures — hidden senders

Each spent input is signed together with **decoy outputs pulled from the chain**. The network
verifies that **one of the outputs was spent (the real one), but cannot tell which**.

- **Monero currently uses a ring size of 16** — **1 real input + 15 decoys**.
- The **upgrade path is FCMP++, in development**. It **replaces ring signatures with full-chain
  membership proofs**: zero-knowledge proofs that an output is **unspent and yours**, over the
  **entire chain's output set**, **eliminating the small-ring anonymity set limitation entirely**.

| Sender-privacy approach | Anonymity set | Status |
|---|---|---|
| Ring signatures, ring size 16 | 1 real + 15 decoys | What Monero uses currently |
| FCMP++ full-chain membership proofs | The entire chain's output set | In development; zero-knowledge proof that an output is unspent and yours |

The ring-signature primitive itself — a group of possible signers with the actual signer hidden
among them — is catalogued in §2 → `coin-cryptographic-primitives`.

### Confidential transactions — hidden amounts

Amounts are hidden in **Pedersen commitments**. The network verifies that **inputs + fee = outputs
without seeing the actual values**.

To prove **no value is created from nothing** — that committed amounts are non-negative — **range
proofs are required**. **Monero uses Bulletproofs+**: compact zero-knowledge range proofs that prove
each committed amount is in **[0, 2^64)** without revealing the amount.

```
Pedersen commitment: C = r*G + v*H  (r = blinding, v = value, G/H = generators)
Verification:        ΣC_inputs = ΣC_outputs + fee*H  (homomorphic property)
Range proof:         prove v ∈ [0, 2^64) without revealing v
```

*Reading the equation above (not an additional source claim):* the fee enters the balance check
explicitly as `fee*H` rather than as a commitment, so the homomorphic sum closes without any party
learning `v`.

### Additional privacy layers in Monero

Three layers sit outside the sender/receiver/amount triad and are part of the same design
commitment:

| Layer | What it does | What it defends against |
|---|---|---|
| **Dandelion++** | Transaction broadcast first propagates through a private **"stem" phase over a chain of peers** before flooding the network | **Network-level IP-to-transaction linkage** — makes it harder |
| **Subaddresses** | **Unlimited unlinkable receive addresses from one wallet seed**, so each counterparty gets a unique address | **On-chain linkage** between a counterparty address and your other addresses |
| **RandomX PoW** | A **CPU-optimized proof-of-work algorithm deliberately designed so that ASICs are uneconomic** | **Hashpower centralization** — keeps mining decentralized on commodity hardware |

Dandelion++ is a networking-layer decision; the gossip and propagation mechanics it modifies are in
§7 → `coin-networking-and-tokenomics`. RandomX as a proof-of-work choice is in §3 →
`coin-consensus-and-finality`.

### THE PRIVACY TRADE-OFF

**Mandatory privacy (Monero's approach) means no anonymity-set fragmentation** — every transaction
looks the same, so **the protection is uniform**. But it also means **the coin cannot be selectively
made transparent for compliance**, which is **why most regulated exchanges have delisted Monero**.

- **The EU's AMLR (Article 79, effective July 2027) bars regulated institutions from servicing
  anonymity-enhancing coins.**
- **Owning and P2P-transferring remains legal in most jurisdictions**, but **the institutional access
  channel is closing**.
- **If you build mandatory privacy into your coin, plan for this regulatory reality from day one.**

This is the concrete downstream cost of the transparent / optional / mandatory privacy decision that
§1 → `coin-what-it-is-and-the-three-architectures` lists as one of the five key design decisions.

### Design consequences to carry into the rest of the build

| Decision | Consequence recorded in this section |
|---|---|
| Choose mandatory privacy | Uniform protection, no anonymity-set fragmentation; regulated-exchange delisting and EU AMLR Article 79 exposure from July 2027 |
| Choose stealth addresses | Wallet must trial-decrypt every output on the chain; no address reuse, so no on-chain address book to analyze |
| Choose ring signatures | Anonymity set is the ring size — currently 16 in Monero, 1 real plus 15 decoys — until FCMP++ replaces it with full-chain membership proofs |
| Choose confidential amounts | Every output needs a Bulletproofs+ range proof over [0, 2^64); balance is checked homomorphically with the fee added explicitly as `fee*H` |
| Choose RandomX | ASICs are uneconomic by design; mining stays on commodity CPU hardware |
| Choose Dandelion++ | Broadcast gains a private stem phase before flooding, raising the cost of IP-to-transaction linkage |

**Bottom line:** privacy is three separate mechanisms plus three supporting layers, every one of which
has to be designed in from the start — and the whole package is the thing regulators, not
cryptographers, will decide the fate of.
