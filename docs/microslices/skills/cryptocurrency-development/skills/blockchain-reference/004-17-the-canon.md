---
id: skill-17-the-canon-600cf8c87f
purpose: 17 the canon
source: src/vibey_tools/skills/plugins/cryptocurrency-development/skills/blockchain-reference/SKILL.md
requires: ["skill-16-currency-snapshot-verified-august-2026-155d46963e"]
links: ["skill-18-quick-reference-e41f8c5e7b"]
---

## §17. The Canon

### 17.1 Primary documentation — read these directly
- **ethereum.org/developers** and the **Ethereum Yellow Paper** (formal EVM spec) and
  **execution-specs** / **consensus-specs** repos — the actual protocol.
- **EIPs.ethereum.org** — every standard, in its authoritative form. **Read the ERC you're
  implementing rather than a blog post about it.**
- **Solidity documentation** (`docs.soliditylang.org`) — including the security
  considerations page and the release blog for the security fixes in each version.
- **Foundry Book** (`getfoundry.sh`) and **Hardhat 3 docs** (`hardhat.org`).
- **OpenZeppelin Contracts** — read the source; it's the reference implementation of most
  standards and the comments are educational.
- **evm.codes** — an interactive opcode reference with gas costs. Indispensable.
- **L2Beat** — the honest L2 risk and stage assessment (§11.1 → `blockchain-protocol-layer`).
- **Forkcast** and the **Ethereum Foundation blog / Protocol Announcements** for upgrade
  status.

### 17.2 Security-specific
**OWASP Smart Contract Top 10** (§10.1 → `blockchain-security-testing-and-ops`'s source), **Smart Contract Weakness Classification
(SWC)**, **Trail of Bits' `building-secure-contracts`** (the best free security curriculum),
**Consensys Smart Contract Best Practices**, **Damn Vulnerable DeFi** and **Ethernaut**
(wargames — **do these; they teach the attacker's perspective faster than any reading**),
**Secureum** and **Cyfrin Updraft**, **rekt.news** (post-mortems — an education in what
actually goes wrong), **Immunefi**, and **DefiLlama's hacks database**.

### 17.3 Books and long-form
| Author | Work |
|---|---|
| **Andreas Antonopoulos & Gavin Wood** | ***Mastering Ethereum*** (free on GitHub) — dated on the roadmap, excellent on fundamentals |
| **Andreas Antonopoulos** | *Mastering Bitcoin* — the clearest explanation of the underlying mechanics |
| **Narayanan et al.** | *Bitcoin and Cryptocurrency Technologies* (Princeton, free) — the academic treatment |
| **Vitalik Buterin** | `vitalik.eth.limo` — the roadmap essays are the primary source on protocol direction |
| **Paradigm, a16z crypto, Flashbots research** | The research blogs where MEV and protocol design get worked out in public |

### 17.4 People and communities
**Ethereum Magicians** (`ethereum-magicians.org` — where EIPs get argued),
**Ethereum Research** (`ethresear.ch`), the **ACD call notes and recordings**,
**Flashbots** (MEV), **samczsun** (the best public incident write-ups in the field),
**Trail of Bits**, **OpenZeppelin**, **Certora**, **Dan Guido**, **Georgios Konstantopoulos**
(Paradigm — Reth, Foundry), **transmissions11**, and **Solidity's own forum and Twitter**
for compiler changes.

---
