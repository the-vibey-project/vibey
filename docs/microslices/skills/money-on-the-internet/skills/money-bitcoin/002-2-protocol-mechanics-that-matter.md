---
id: skill-2-protocol-mechanics-that-matter-5a07c6ec5c
purpose: 2 protocol mechanics that matter
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-bitcoin/SKILL.md
requires: ["skill-1-what-it-is-93e2a2ccad"]
links: ["skill-3-using-bitcoin-well-aae06dc179"]
---

## 2. Protocol mechanics that matter

**[DURABLE]** Throughout.

- **Mining = Sybil-resistant leader election.** Miners grind SHA-256d over block headers to find a hash under the difficulty target; each block commits to a Merkle tree of transactions. Energy expenditure — not identity — is what makes rewriting history expensive.
- **Script.** Each output carries a locking script; spending provides an unlocking script. Bitcoin Script is intentionally not Turing-complete (no loops). Everything you know — multisig, timelocks (`OP_CHECKLOCKTIMEVERIFY`/`OP_CHECKSEQUENCEVERIFY`), HTLCs for Lightning — is built from this small vocabulary.
- **SegWit (2017, BIP-141)** moved signatures ("witnesses") out of the base block, fixing transaction malleability and enabling both Lightning and the modern address formats. **Taproot (Nov 2021, BIP-340/341/342)** replaced ECDSA with Schnorr signatures (linear, aggregatable, enabling MuSig2) and committed scripts into a Merkle tree (MAST) so that the common key-spend path looks identical to a plain payment — a privacy and efficiency win.
- **Address types** you'll handle as a developer: legacy Base58 (`1…` P2PKH, `3…` P2SH), **bech32 SegWit v0 (`bc1q…`)**, **bech32m Taproot v1 (`bc1p…`)**. **[⚠️ bech32 (BIP-173) has a length-extension weakness; it's only correct for v0. Use bech32m (BIP-350) for anything else.]**
- **Fee machinery**: RBF (BIP-125, opt-in replace-by-fee), CPFP (child-pays-for-parent), **TRUC "v3" transactions (BIP-431)** constraining replacement topology, and package relay. As of Core 31 (§6) the ancestor/descendant model was replaced by **cluster mempool** — if you build fee-bumping tooling, that release is your new reference point.
- **Sighash flags** (`SIGHASH_ALL` etc.) define what a signature commits to; Taproot's `SIGHASH_DEFAULT` is now the common case.
- **Silent Payments (BIP-352)** — reusable static payment codes where the sender derives a fresh on-chain address without any interaction; receiving wallets must scan with their private key, which is the adoption cost.

---
