---
id: skill-4-the-qubic-affair-aug-2025-what-a-51-attack-actually-looks-like-contested-interpretation-bf03d70fb7
purpose: 4 the qubic affair aug 2025 what a 51 attack actually looks like contested interpretation
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-monero/SKILL.md
requires: ["skill-3-fcmp-the-upgrade-that-matters-and-its-real-status-versioned-verify-before-relying-478518c59d"]
links: ["skill-5-using-monero-in-2026-access-is-the-hard-part-a1ba946370"]
---

## 4. The Qubic affair (Aug 2025) — what a "51% attack" actually looks like — [CONTESTED interpretation]

The timeline ([Cointelegraph](https://cointelegraph.com/news/monero-qubic-selfish-mining-51-percent-attack), [The Block](https://www.theblock.co/post/366535/monero-faces-chain-reorganization-fears-after-qubic-says-it-controls-51-of-hashrate), [Protos](https://protos.com/qubic-failed-to-51-attack-monero-but-dogecoin-is-next/), [DL News](https://www.dlnews.com/articles/defi/monero-hashrate-tug-war-ease-qubic-lose-51-percent-dominance/)):

- Qubic (Sergey Ivancheglo's L1) ran a months campaign paying miners **more than Monero's block reward** to mine XMR (funding it via QUBIC token buybacks) — an *economic* attack, not a technical one. Its hashrate share went <2% (May) → 25–45% (July).
- **11–12 Aug 2025**: Qubic claimed >50% and produced a **six-block-deep reorganization orphaning ~60 blocks**. XMR fell ~8–11%; Kraken, MEXC, HTX, WhiteBIT and swap services paused XMR moves (most resumed within days).
- **The dispute**: Ledger's CTO called it "a successful 51% attack"; Monero-side researchers and an analysis **commissioned by Qubic itself** (the "Minority Report," Shai Wyborski) estimated the real share at **28–35%**, achieved via **selfish mining** — withholding blocks to orphan rivals, which *simulates* majority dominance. No double-spends were found (BitMEX Research); Ivancheglo later joked it was a "**34% attack**." By 17 Aug the share had fallen back to ~35%. Qubic then pivoted to targeting Dogecoin.

**[DURABLE] lessons for any PoW builder/user**: (1) security budget = honest cost of attacking ≈ what honest miners earn; small PoW chains are attackable *by bribery*, not just by owned hardware; (2) selfish mining degrades a chain well below the 51% threshold — deep reorgs can happen at ~⅓ share; (3) "attacker got lucky with 30%" and "attacker has majority control" can look identical from outside; verify via orphan rate patterns, not press releases; (4) exchanges' defense-in-depth reaction (pausing deposits) is the correct operational response and your app should be built to tolerate it.

---
