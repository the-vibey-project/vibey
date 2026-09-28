---
id: skill-1-side-by-side-all-dated-claims-are-as-of-16-sep-2026-6c29ae4f33
purpose: 1 side by side all dated claims are as of 16 sep 2026
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-choosing-a-rail-and-shared-patterns/SKILL.md
requires: []
links: ["skill-2-decision-heuristics-54ba0e9f84"]
---

## 1. Side-by-side (all dated claims are "as of 16 Sep 2026")

| Dimension | Bitcoin | Ethereum | Monero | PayPal | Stripe |
|---|---|---|---|---|---|
| Settlement finality | ~probabilistic; 6 conf ≈ 1 h | ~13 min cryptographic | ~20 min convention (10 blk) | Ledger-instant, fiat behind it | Same |
| Reversible by operator? | No | No | No | **Yes** — disputes, holds, freezes | **Yes** — disputes, reserves, termination |
| Typical fee to accept $100 (US) | on-chain: sub-$1-ish in 2026's fee regime, spiky; LN ~0.01–0.05% | $0.003–0.25 L1 typical; L2s fractions of a cent | cents | $3.98 (3.49%+$0.49) | $3.20 (2.9%+$0.30); stablecoin payout 1.5% |
| Programmability | Script, PSBT, miniscript, Lightning | Full EVM | None | REST APIs + PYUSD contracts (ETH/SOL…) | Everything: Payments/Billing/Connect/Issuing/Tax + stablecoin stack |
| Privacy | Pseudonymous/public | Pseudonymous/public | **Default-private (ring-16, RingCT, stealth)** | KYC institution | KYC institution |
| Custody model | Self or custodian (ETFs) | Self/smart accounts/custodian | Self | PayPal custodies | Stripe custodies |
| Regulatory temperature (Sep 2026) | ETFs live; CLARITY failed 15 Sep; strategic-reserve bills pending | Same + GENIUS governs its stablecoin economy | **Coldest**: EU AMLR bar effective Jul 2027; India FIU directive; EEA delisted on Kraken | Licensed money transmitter; PYUSD under GENIUS regime | Same, plus Bridge's conditional OCC trust charter (Feb 2026) |
| Dev maturity | v31 Core, BDK/LDK mature, dev docs scattered | Best-in-class tooling (Foundry/HH3, viem) | monerod/wallet-rpc solid; library ecosystem thin | REST v2 + Braintree mature | Deepest API surface; best docs in payments |
| Failure mode you're insuring | Key loss, protocol risk, mempool policy shifts | Contract bugs, key theft, phishing | Exchange illiquidity, reorgs, regulation | Chargebacks, holds, freezes | Same + platform/price risk |
