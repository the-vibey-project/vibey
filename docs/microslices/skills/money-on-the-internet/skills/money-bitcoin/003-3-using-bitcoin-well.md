---
id: skill-3-using-bitcoin-well-aae06dc179
purpose: 3 using bitcoin well
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-bitcoin/SKILL.md
requires: ["skill-2-protocol-mechanics-that-matter-5a07c6ec5c"]
links: ["skill-4-the-lightning-network-payments-layer-2d4ceb5891"]
---

## 3. Using Bitcoin well

**Custody is the whole game.** Key management standards you'll meet everywhere, **[DURABLE]**:
- **BIP-39** seed phrases (human-readable backup; the passphrase option is a plausible-deniability/decoy layer, and a loss vector).
- **BIP-32** hierarchical-deterministic derivation; **BIP-44/49/84/86** account/purpose paths by script type.
- **Descriptors (BIP-380s family)** — strings like `wpkh(xpub…/0/*)` that fully describe a wallet's script structure; the modern interchange format between Core and signing devices.
- **PSBT (BIP-174)** — partially signed transactions passed between coordinator and signers; the backbone of multisig, coinjoin, hardware-wallet and Lightning-splice workflows.

Practical usage rules:
- Verify receive addresses **on the signing device's screen**, not on a potentially compromised host.
- Multisig of 2-of-3 across vendors/geographies is the standard for serious holdings; coordinate it with descriptors + PSBTs, and store the descriptor with each seed (a seed without its derivation path/script info can be an unrecoverable lockbox).
- **[⚠️ Address reuse damages your privacy permanently]** — the ledger is public forever; every serious wallet rotates addresses. Silent Payments (above) are the emerging answer for published donation-style codes.
- Confirmation targets: 1 conf is fine for retail-sized amounts; 3–6 for meaningful value; **be suspicious of 0-conf acceptance from strangers** — RBF exists, and 0-conf is a promise, not a payment.
- Regulated access: US spot Bitcoin ETFs (live since Jan 2024) made brokerage-account exposure routine — with all the tradeoffs of custodial IOUs (you hold a fund share, not keys; Sept 2026's $450M single-day ETF outflow is a reminder that this channel amplifies sentiment swings).

---
