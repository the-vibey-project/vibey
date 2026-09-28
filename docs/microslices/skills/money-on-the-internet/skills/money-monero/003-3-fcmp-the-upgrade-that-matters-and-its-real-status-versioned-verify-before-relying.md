---
id: skill-3-fcmp-the-upgrade-that-matters-and-its-real-status-versioned-verify-before-relying-478518c59d
purpose: 3 fcmp the upgrade that matters and its real status versioned verify before relying
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-monero/SKILL.md
requires: ["skill-2-the-privacy-stack-durable-356e0ce8a9"]
links: ["skill-4-the-qubic-affair-aug-2025-what-a-51-attack-actually-looks-like-contested-interpretation-bf03d70fb7"]
---

## 3. FCMP++: the upgrade that matters, and its real status — [VERSIONED, verify before relying]

**What it is**: replacing 16-decoy ring signatures with **Full-Chain Membership Proofs** — zero-knowledge proofs that an output is unspent and yours, over *the entire chain output set* (~100M+ outputs), built on Curve Trees with new Helios/Selene curves. Ships with **CARROT** (new backward-compatible addressing), forward secrecy, and outgoing view keys. Trade-offs: ~2.7 KB per input and heavier verification.

**Status as of 16 Sep 2026 — not on mainnet.** Mainnet still runs 16-member rings; latest releases are **CLI 0.18.5.1 "Fluorine Fermi" (8 Jul 2026)** and **GUI 0.18.5.2 (21 Jul 2026)**. FCMP++/CARROT live under the `v0.19.0.0-alpha` stressnet line:
- Public **beta stressnet launched 6 May 2026** (forked at block 2,997,100); earlier CARROT alpha stressnet 8 Jan 2026; `unlock_time` deprecation announced 10 May 2026 as prep ([CoinVast explainer](https://coinvast.io/articles/monero-fcmp-upgrade-explained)).
- Audits: **Veridise** (Apr–May 2025, circuit soundness); **Trail of Bits** integration review (May 2026); **ToB cryptography-implementation audit announced 17 Aug 2026 — 6 informational findings, zero high/medium/low, 5 resolved** ([MAGIC Grants](https://magicgrants.org/2026/08/17/Monero-FCMP-Cryptography-Implementation-ToB)).
- Active dev in `monero-oxide/monero-oxide` (fcmp++ branch) and the main repo (e.g. PR #10724 "curve tree builder" under milestone `fcmp++ hf`).
- **No committed mainnet fork date.** Outside estimates (not project commitments) run roughly **Nov 2026 – May 2027**, based on Monero's historical stressnet→mainnet cadence.
- ⚠️ **Widespread misreporting in 2026 claimed FCMP++ had already activated on mainnet** — that conflates the May stressnet with mainnet. Check the fork height on the daemon's `hard_fork_info` rather than the press.

---
