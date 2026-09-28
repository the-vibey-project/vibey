---
id: skill-9-security-what-actually-loses-money-15b470d80e
purpose: 9 security what actually loses money
source: src/vibey_tools/skills/plugins/building-a-cryptocurrency/skills/coin-security-and-the-build-guide/SKILL.md
requires: []
links: ["skill-10-practical-building-guide-200a436140"]
---

## §9 Security: What Actually Loses Money

The security landscape for cryptocurrencies is unlike any other software domain. Deployed code is adversarial code running in public with money attached. Every function is callable by anyone, in any order, at any time, composed with contracts that don't exist yet, by attackers who read your source and have unlimited attempts. And you cannot patch it — immutability is the point and also the problem.

### The vulnerability canon — know these cold

The 2025-2026 incident data is unambiguous about what loses money, and it should reorder your priorities.

| Category | 2025 losses (full year) | What It Is | Defense |
|---|---|---|---|
| Access control | ~$953M | Missing or incorrect permission checks on privileged functions; unprotected initializers or upgrade paths | Audit every privileged path. Use `Ownable2Step` or `AccessControl`. Timelocks on upgrades. |
| Logic errors | ~$64M | Incorrect business logic — wrong math, wrong conditions, unexpected state transitions | Formal verification. Invariant testing. Multiple audits. |
| Reentrancy | ~$36M | External call before state update allows re-entry that exploits stale state | Checks-Effects-Interactions ordering. `nonReentrant` guards. Watch cross-function and read-only reentrancy. |
| Flash loan exploits | ~$34M | Flash loans give attackers unlimited capital for one transaction, amplifying existing vulnerabilities | Assume every attacker has unlimited capital. Don't read DEX spot prices as oracle values. Use Chainlink/Pyth or TWAPs. |

**Phishing is measured over a different period, so it gets its own table.** The source's figure for
it covers **Q1 2026 alone** — one quarter, against four full-year-2025 categories above. The two sets
are not summable and not rankable against each other as they stand:

| Category | Q1 2026 losses (one quarter) | What It Is | Defense |
|---|---|---|---|
| Phishing / social engineering | ~$306M | Tricking users into signing malicious transactions or revealing keys | Show users what they're signing in human-readable terms. No blind signing. Hardware wallets. Education. |

> **THE PRIORITY REORDERING — AND WHICH DATASET EACH CLAIM RESTS ON**
>
> **From the 2025 full-year column.** Access control vulnerabilities cause roughly **fifteen times**
> the loss of logic errors and **twenty-seven times** reentrancy (computed from that table:
> 953/64 ≈ 14.9 and 953/36 ≈ 26.5). The most devastating attacks don't exploit exotic cryptography —
> they exploit mundane permission mistakes. These four categories are comparable with each other
> because they share a period.
>
> **From the Q1 2026 data.** The source reports that phishing and social engineering account for
> **nearly two-thirds of losses** in that period, and that code audits have pushed smart-contract
> exploit losses down **~89% year-over-year**. That two-thirds is the source's own figure: **the Q1
> 2026 total across all categories is not given here**, so the share cannot be recomputed from the
> ~$306M, and ~$306M in a quarter must not be set beside the 2025 rows as though the periods matched.
>
> **What the two datasets agree on** is the direction, and that is what should reorder your
> priorities: the attackers moved to the humans. Your security budget is probably misallocated if
> it's all on code audits and none on key management, operational security, and social-engineering
> resistance.

### The design principles that prevent most bugs

- **Checks-Effects-Interactions** — validate inputs first, then update your state, then make external calls. This ordering alone prevents most reentrancy. If you must call an external contract before updating state, use a reentrancy guard (a transient-storage lock).
- **Pull over push** — let users withdraw their funds rather than pushing payments to them. If you push and one recipient's contract reverts, it can block everyone's payment. With pull, one user's failure doesn't affect others.
- **Fail loudly** — revert with custom errors rather than returning `false`. A silent failure that goes unchecked is worse than a loud one.
- **Bound every loop** — unbounded loops over user-controlled arrays are a permanent denial-of-service. If the array grows past the block gas limit, the function is uncallable forever — and if it guards fund withdrawal, the funds are locked permanently.
- **Minimize privileged surface** — every privileged function is an attack target. Use multisig (Safe is the standard) plus timelock for anything that can drain or brick the system. Never use an EOA as the owner of a contract holding real value.
- **Never use `tx.origin` for authorization** — `tx.origin` is the original EOA that initiated the transaction. Any contract the user calls can relay a call to your contract and pass the check. This is a textbook phishing vector. Always use `msg.sender`.
- **Never read a DEX spot price as "the price"** — a flash loan can move a DEX pool price in a single transaction. Use Chainlink, Pyth, RedStone, or a TWAP over a meaningful window. Check the oracle's staleness and the L2 sequencer uptime feed.

### Key management — the hardest part

The algorithm choice is usually easy and usually not where you lose. **Where keys live, who can reach them, and how they rotate is where systems actually fail.** Hard-won lessons: hardware wallets for anything meaningful. Multisig (Safe) for protocol control. Verify what you're signing — blind signing is how multisig holders get drained. Separate deploy keys from admin keys from operational keys. Never put a private key or mnemonic in a repository, an env file, or a CI log. **Key compromise produced the largest single losses in 2026's incident data.**
