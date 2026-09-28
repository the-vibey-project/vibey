---
id: skill-10-security-804287b292
purpose: 10 security
source: src/vibey_tools/skills/plugins/cryptocurrency-development/skills/blockchain-security-testing-and-ops/SKILL.md
requires: ["skill-9-testing-f19c0c6124"]
links: ["skill-13-deployment-and-operations-5cbcf79699"]
---

## §10. Security

### 10.1 What actually loses money — start here

**[VERSIONED, and it should reorder your priorities.]** The empirical picture from 2025–2026
incident data is unambiguous and does not match where most developer attention goes.

**By loss category** (OWASP Smart Contract Top 10 for 2026, built from 2025 incident data
across 149 documented incidents totalling ~$1.42B):
```
Access control vulnerabilities   $953.2M   ← the overwhelming majority
Logic errors                      $63.8M
Reentrancy                        $35.7M
Flash loan exploits               $33.8M
```
**⚠️ Read that again. Access control is roughly fifteen times the loss of logic errors and
twenty-seven times reentrancy.** The most devastating attacks don't exploit exotic
cryptography — **they exploit mundane permission mistakes.** Hacken's 2025 data agrees:
access-control exploits drove ~59% of total losses, smart-contract vulnerabilities ~8%.

**And the bigger shift [VERSIONED]:** **smart contract exploit losses fell ~89%
year-over-year in Q1 2026** per DefiLlama — audits and architecture are working — **and it
didn't reduce total losses, because attackers moved to the humans.** Q1 2026 saw ~$450M lost
across 145 incidents, of which **phishing and social engineering accounted for ~$306M,
nearly two-thirds**. A single January social-engineering attack drained **$282M without
touching a line of code.** Six audited protocols were breached in that quarter; **one had
passed 18 prior audits.**

**⚠️ The operational consequence: your security budget is probably misallocated.** Code
audits address code vulnerabilities. They would not have prevented the largest 2026
incidents. **Key management, operational security, insider risk, and social-engineering
resistance now deserve first-class attention alongside the audit** — and note that
**Chainalysis attributes roughly 76% of 2026 crypto hack losses to state-backed actors
linked to Lazarus Group**, whose approach includes six-month social-engineering campaigns
and embedding operatives as IT workers. That is a different threat model than "did we
check-effects-interactions correctly."

### 10.2 The vulnerability canon

**[DURABLE] Know these cold. Most exploits are known classes hitting code that skipped
review, not zero-days.**

| Class | Mechanism | Defense |
|---|---|---|
| **Broken access control** | Missing/incorrect modifier; unprotected initializer or upgrade | §6.2 → `blockchain-smart-contract-development`. **Audit every privileged path** |
| **Reentrancy** | External call before state update; also **cross-function** and **read-only** (view function returns stale mid-transaction state) | **Checks-Effects-Interactions**; `nonReentrant`; transient storage |
| **Oracle manipulation** | Spot price from a manipulable source | §8.2 → `blockchain-smart-contract-development` |
| **Integer issues** | Overflow on pre-0.8 or in `unchecked`; **precision loss from division-before-multiplication**; rounding in the protocol's favour | 0.8+; order operations carefully; round deliberately |
| **Unchecked return values** | `call`/`send`/non-standard ERC-20 silently failing | Check returns; `SafeERC20` |
| **DoS** | Unbounded loops; a reverting recipient blocking a queue; gas griefing | Bound loops; **pull over push** |
| **Front-running / MEV** | Ordering | Slippage limits, deadlines, commit-reveal (§8.4 → `blockchain-smart-contract-development`) |
| **Signature issues** | Replay across chains/contracts, missing nonce, **`ecrecover` malleability**, signatures for the zero address | EIP-712 with full domain; nonces; OZ `ECDSA` |
| **Weak randomness** | `block.timestamp`, `blockhash`, `block.prevrandao` | **On-chain randomness is not private.** Use a VRF |
| **Delegatecall to untrusted code** | Attacker controls your storage | Never delegatecall to user input |
| **Uninitialized proxies** | §6.1 → `blockchain-smart-contract-development` | `_disableInitializers()` |
| **First-depositor / donation** | Share-price manipulation in vaults | Virtual shares; seed the vault |
| **Price/liquidity assumptions** | Assuming deep liquidity, or a pool that can't be drained | Model the adversarial case |

### 10.3 Beyond the code

**⚠️ Verify your contracts on the block explorer.** Chainalysis documented five protocols
in six months where the **exploited contract was the protocol's own and was unverified**,
totalling ~$36.7M — and noted that in an era of easy decompilation, unverified code buys you
nothing while destroying user trust and third-party review.

**Bug bounties** (Immunefi is the venue) are cheap relative to an exploit. **Monitoring and
incident response** — Forta, OpenZeppelin Defender, custom watchers — plus a **rehearsed
pause procedure**. **Timelocks** give users an exit window. And **[VERSIONED] the rise of
AI-assisted exploit development is likely accelerating**, per Chainalysis — the attacker's
cost of finding a bug in public bytecode is falling.

**Audit reality check**: costs range from roughly $3,000 for a simple contract to $100,000+
for complex multi-contract systems. **⚠️ An audit is a snapshot of specific code at a
specific commit by fallible humans under time pressure. It is not a guarantee**, as the
protocol with 18 prior audits demonstrated. Get multiple audits for high value, fix
findings *and* their root causes, and re-audit after changes.

---
