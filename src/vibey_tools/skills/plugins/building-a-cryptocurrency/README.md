# Building a Cryptocurrency Plugin

How to design and ship your own chain, from the cryptographic primitives up — with enough
detail to actually build one in the style of Bitcoin, Ethereum or Monero.

One reference, split into 8 skills, so a task loads only the part it needs.

**The definition everything else hangs off:**

> A cryptocurrency is a **replicated state machine** with **Sybil-resistant leader election** and a
> **fork-choice rule**, producing eventual (or explicit) agreement on an ordered log of transactions.
> Everything else — the token, the wallets, the smart contracts, the governance — is built on top of
> that foundation.

And every major chain is a variation on one of **three reference architectures**: Bitcoin's UTXO
ledger, Ethereum's account-and-code model, and Monero's privacy-enhanced UTXOs. Understanding how
they differ on ledger model, consensus, finality, programmability and privacy is what lets you
choose deliberately rather than by imitation.

## ⚠️ Scope and disclaimer

This is an **engineering reference, not investment advice**. Creating a cryptocurrency is a
legitimate software engineering exercise with well-documented open-source reference implementations.

But deploying one that handles real value carries serious legal, financial and security
responsibilities. **Consult counsel** regarding securities law, AML/KYC requirements and consumer
protection regulations in your jurisdiction before launching anything that distributes tokens to the
public. The skills carry this forward wherever they touch issuance, distribution or sale.

## The skills

| Skill | Sections | Covers |
|---|---|---|
| `coin-what-it-is-and-the-three-architectures` | §1 | The replicated-state-machine definition, the Bitcoin/Ethereum/Monero comparison, and the five design decisions that follow |
| `coin-cryptographic-primitives` | §2 | Hashes and the length-extension attack, ECDSA/Schnorr/Ed25519 and the nonce hazard, Merkle trees and tries, HD wallets and key management |
| `coin-consensus-and-finality` | §3 | Proof of work, proof of stake, Sybil resistance, fork choice, and what finality actually promises |
| `coin-building-a-utxo-chain` | §4 | The UTXO model, script, validation, and what forking Bitcoin actually involves |
| `coin-building-an-account-chain` | §5 | The account and world-state model, the EVM, gas, and shipping smart contracts |
| `coin-privacy-features` | §6 | Ring signatures, stealth addresses, confidential amounts, zero-knowledge approaches |
| `coin-networking-and-tokenomics` | §7–§8 | Peer-to-peer gossip and block propagation, then issuance, fees, supply and incentive design |
| `coin-security-and-the-build-guide` | §9–§10 | What actually loses money, and the ordered guide to building and launching |

Section numbers are **shared across the set**: a reference written as `§N → skill` points into that
sibling skill.

## Neighbours in this marketplace

Three plugins touch this ground from different directions, and the distinction is worth keeping:

- **`building-a-cryptocurrency`** (this one) — you are building **the chain itself**.
- **`cryptocurrency-development`** — you are building **on** an existing chain: Solidity and Vyper,
  contract architecture and upgradeability, ERC standards, DeFi primitives and MEV, Foundry and
  Hardhat, fuzzing and formal verification, deployment and key management.
- **`money-on-the-internet`** — you are **using** a rail, or accepting payment on one: Bitcoin,
  Ethereum, Monero, PayPal and Stripe positioned against each other on finality, censorship,
  programmability, privacy and cost.

Also adjacent: `cryptography-and-encryption` for the primitives as a discipline, and
`quantum-cryptography-and-quantum-internet` for the post-quantum question.
