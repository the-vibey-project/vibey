---
id: skill-15-contested-questions-9ccfe96fc7
purpose: 15 contested questions
source: src/vibey_tools/skills/plugins/cryptocurrency-development/skills/blockchain-reference/SKILL.md
requires: ["skill-14-anti-patterns-d03ebea940"]
links: ["skill-16-currency-snapshot-verified-august-2026-155d46963e"]
---

## §15. Contested Questions

**15.1 Upgradeable vs. immutable.** §6.1 → `blockchain-smart-contract-development`. The genuinely hard one. The middle position most
serious protocols land on: **upgradeable behind a timelock and a multisig, with a credible
path to eventual immutability**, so users can exit before any change takes effect.

**15.2 Solidity vs. Vyper.** §5.2 → `blockchain-smart-contract-development`. Vyper's restrictions are a real security argument;
against it, ecosystem size and its own compiler-bug history. **The deeper point either way:
the compiler is part of your trust surface.**

**15.3 Foundry vs. Hardhat.** §9.1 → `blockchain-security-testing-and-ops` — and this genuinely changed. The speed and
Solidity-testing arguments that decided it in 2022 are much weaker now that Hardhat 3 is
within ~2× and has native Solidity tests. **The 2026 answer is often "both, for different
phases."**

**15.4 Optimistic vs. ZK rollups.** Optimistic: simpler, mature, cheap to prove, 7-day
withdrawals. ZK: fast finality, higher proving cost and complexity, less mature tooling.
**The gap has narrowed considerably**; the honest answer depends on your withdrawal-latency
requirement and your tolerance for a younger stack.

**15.5 Monolithic vs. modular blockchains.** Modular (separate execution, settlement,
consensus, DA) versus doing it all in one chain. *Modular*: specialization and scaling.
*Monolithic*: composability, simpler security reasoning, no fragmented liquidity. Ethereum
has bet decisively on modular via rollups; several competitors have not.

**15.6 Is an L2 "Ethereum"?** A real ecosystem argument about whether rollup-centric scaling
delivers Ethereum's security guarantees to users in practice, given centralized sequencers,
upgrade keys, and bridge risk. **L2Beat's stage framework exists precisely because the
answer is "it depends on the specific L2."**

**15.7 Does decentralization survive the incentives?** Staking concentration, MEV relay
centralization, RPC-provider concentration, and client supermajorities are all real
measured pressures against the stated design goals. **The protocol roadmap (ePBS, FOCIL,
PeerDAS, statelessness) is substantially a response to this**, which is itself an
acknowledgment that the concern is legitimate.

---
