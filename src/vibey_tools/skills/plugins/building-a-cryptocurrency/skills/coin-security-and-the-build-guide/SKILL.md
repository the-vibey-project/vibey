---
name: coin-security-and-the-build-guide
description: "Use when auditing a chain or a contract for the failures that actually drain funds, choosing between an ERC-20 token, an L2 rollup and a new blockchain, picking the language, consensus, signature, wallet and explorer stack for a custom chain, or working a pre-mainnet launch checklist. Covers the 2025-2026 loss data, the design principles and key-management rules that prevent most bugs, and the three build paths with their timelines. Part 8 of 8 of the Building a Cryptocurrency reference."
---

# Security and the Practical Build Guide

> **Part 8 of 8** of the *Building a Cryptocurrency* reference (plugin
> `building-a-cryptocurrency`), covering §9–§10 — what actually loses money, and the ordered guide to building and launching a chain. Sibling skills:
> `coin-what-it-is-and-the-three-architectures` (§1 — the replicated-state-machine definition and the Bitcoin / Ethereum / Monero reference architectures),
> `coin-cryptographic-primitives` (§2 — the hashes, signatures, key derivation and commitment schemes a chain is built from),
> `coin-consensus-and-finality` (§3 — proof of work, proof of stake, Sybil resistance, fork choice and what finality actually means),
> `coin-building-a-utxo-chain` (§4 — the UTXO ledger model, script, transaction validation and what a fork of Bitcoin actually involves),
> `coin-building-an-account-chain` (§5 — the account/world-state model, the EVM, gas, and building a chain with smart contracts),
> `coin-privacy-features` (§6 — ring signatures, stealth addresses, confidential amounts and zero-knowledge approaches),
> `coin-networking-and-tokenomics` (§7–§8 — peer-to-peer gossip and propagation, then issuance, fees, supply schedules and incentive design),
>
> Section numbers are **shared across the whole set**: a reference written as §N → `skill` points
> into that sibling skill. This is an engineering reference, **not investment, legal or tax advice** —
> deploying a chain that handles real value carries securities, AML/KYC and consumer-protection
> obligations that are a question for counsel in your jurisdiction.

> **SCOPE AND DISCLAIMER** — carried forward verbatim from the front of the source document, because §10 covers launching, distributing and selling tokens.
> This is an engineering reference, not investment advice. Creating a cryptocurrency is a legitimate software engineering exercise with well-documented open-source reference implementations. However: deploying a cryptocurrency that handles real value carries serious legal, financial, and security responsibilities. Consult counsel regarding securities law, AML/KYC requirements, and consumer protection regulations in your jurisdiction before launching anything that distributes tokens to the public.

## §9 Security: What Actually Loses Money

The security landscape for cryptocurrencies is unlike any other software domain. Deployed code is adversarial code running in public with money attached. Every function is callable by anyone, in any order, at any time, composed with contracts that don't exist yet, by attackers who read your source and have unlimited attempts. And you cannot patch it — immutability is the point and also the problem.

### The vulnerability canon — know these cold

The 2025-2026 incident data is unambiguous about what loses money, and it should reorder your priorities.

| Category | 2025 Losses | What It Is | Defense |
|---|---|---|---|
| Access control | ~$953M | Missing or incorrect permission checks on privileged functions; unprotected initializers or upgrade paths | Audit every privileged path. Use `Ownable2Step` or `AccessControl`. Timelocks on upgrades. |
| Logic errors | ~$64M | Incorrect business logic — wrong math, wrong conditions, unexpected state transitions | Formal verification. Invariant testing. Multiple audits. |
| Reentrancy | ~$36M | External call before state update allows re-entry that exploits stale state | Checks-Effects-Interactions ordering. `nonReentrant` guards. Watch cross-function and read-only reentrancy. |
| Flash loan exploits | ~$34M | Flash loans give attackers unlimited capital for one transaction, amplifying existing vulnerabilities | Assume every attacker has unlimited capital. Don't read DEX spot prices as oracle values. Use Chainlink/Pyth or TWAPs. |
| Phishing / social engineering | ~$306M (Q1 2026) | Tricking users into signing malicious transactions or revealing keys | Show users what they're signing in human-readable terms. No blind signing. Hardware wallets. Education. |

> **THE PRIORITY REORDERING**
> Access control vulnerabilities cause roughly **fifteen times** the loss of logic errors and **twenty-seven times** reentrancy. (Computed from the table above: 953/64 ≈ 14.9 and 953/36 ≈ 26.5.) The most devastating attacks don't exploit exotic cryptography — they exploit mundane permission mistakes. And in 2026, phishing and social engineering account for **nearly two-thirds of all losses**, because code audits have pushed smart-contract exploit losses down **~89% year-over-year**. The attackers moved to the humans.
> Your security budget is probably misallocated if it's all on code audits and none on key management, operational security, and social-engineering resistance.

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

## §10 Practical Building Guide

### Option A: launching an ERC-20 token (days to weeks)

This is the fastest path to a cryptocurrency. You're deploying a smart contract on an existing blockchain (Ethereum, an L2, or another EVM chain), **not creating a new blockchain**. The contract defines the token's supply, transfer rules, and any additional functionality. (The EVM, gas and the ERC-20 interface itself: §5 → `coin-building-an-account-chain`.)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable2Step.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
/// @title MyCoin — a simple ERC-20 with fixed supply and vesting
contract MyCoin is ERC20, Ownable2Step, ReentrancyGuard {
    uint256 public constant TOTAL_SUPPLY = 100_000_000 * 10**18; // 100M to
    struct VestingSchedule {
        uint256 totalAmount;
        uint256 claimed;
        uint256 startTimestamp;
        uint256 durationSeconds;
    }
    mapping(address => VestingSchedule) public vesting;
    event VestingSet(address indexed beneficiary, uint256 amount, uint256 d
    constructor() ERC20("MyCoin", "MYC") Ownable(msg.sender) {
        _mint(address(this), TOTAL_SUPPLY);
    }
    /// @notice Set vesting for a team member or investor
    function setVesting(address beneficiary, uint256 amount, uint256 durati
        external
        onlyOwner
    {
        require(vesting[beneficiary].totalAmount == 0, "Already vested");
        require(amount <= balanceOf(address(this)), "Insufficient balance")
        vesting[beneficiary] = VestingSchedule({
            totalAmount: amount,
            claimed: 0,
            startTimestamp: block.timestamp,
            durationSeconds: duration
        });
        emit VestingSet(beneficiary, amount, duration);
    }
    /// @notice Claim vested tokens
    function claimVesting() external nonReentrant {
        VestingSchedule storage v = vesting[msg.sender];
        require(v.totalAmount > 0, "No vesting");
        uint256 elapsed = block.timestamp - v.startTimestamp;
        uint256 vested = (v.totalAmount * elapsed) / v.durationSeconds;
        uint256 claimable = vested - v.claimed;
        require(claimable > 0, "Nothing to claim");
        v.claimed += claimable;
        _transfer(address(this), msg.sender, claimable);
    }
}
```

Four lines above are clipped at the right margin in the source document — the `TOTAL_SUPPLY` comment, the `VestingSet` event signature, the `setVesting` signature, and the trailing semicolon of the balance `require`. They are reproduced exactly as the source renders them rather than reconstructed.

**What you need to do:** write the contract; test it with Foundry (unit tests, fuzzing, invariant testing); get it audited; deploy to a testnet (Sepolia, Holesky); exercise it; deploy to mainnet; verify the source on Etherscan; transfer ownership to a multisig + timelock; write an incident runbook.

### Option B: launching an L2 rollup (weeks to months)

If you want your own execution environment and fee market but don't want to bootstrap security from scratch, an L2 rollup inherits the L1's security. **OP Stack** (Optimism's stack) is the most established path for optimistic rollups; **ZK Stack** and **Polygon CDK** for ZK rollups. The trade-off: your chain depends on the L1 for data availability and settlement. Most rollups currently run a **centralized sequencer** (a censorship and liveness single point of failure), with forced inclusion via L1 as the escape hatch.

The three security questions to ask of any L2: **who can censor you, who can steal from you, and can you exit without permission?**

### Option C: building a new blockchain (months to years)

If you need a fully independent blockchain, this is the most ambitious path. You need to build or assemble:

1. **Node software** — the full node that validates transactions, maintains state, participates in consensus, and serves RPC. Bitcoin Core is ~400K lines of C++. Geth is ~300K lines of Go. You can start from a fork of an existing codebase (many coins are forks of Bitcoin Core or Go-Ethereum) or build from scratch.
2. **Consensus mechanism** — PoW (need a mining algorithm, difficulty adjustment), PoS (need staking, slashing, validator management), or BFT (need a validator set, voting protocol). Each has its own failure modes and complexity. (§3 → `coin-consensus-and-finality`.)
3. **P2P networking** — peer discovery, message propagation, block relay. This is often the most underappreciated component — a network that propagates blocks slowly is vulnerable to centralization. (§7 → `coin-networking-and-tokenomics`.)
4. **Wallet software** — key management, transaction signing, balance viewing. For UTXO chains, this includes coin selection and fee estimation. For account chains, this includes nonce management and gas estimation. Hardware wallet support is expected.
5. **Block explorer** — a web interface for viewing blocks, transactions, and addresses. Without this, no one can independently verify what's happening on your chain.
6. **Developer tooling** — SDKs for at least one major language (TypeScript, Python, Rust), RPC documentation, CLI tools. Without tooling, no one will build on your chain.
7. **Bootstrap community** — miners or validators, exchanges (if you want listings), wallet providers, developers, users. **This is the hardest part and the most important — a blockchain with no users is just a database.**

### Technology choices for a custom chain

| Component | Bitcoin-Style | Ethereum-Style | Privacy-Style |
|---|---|---|---|
| Language | C++, Rust | Go, Rust, C# | C++, Rust |
| Ledger | UTXO set | Account trie | UTXO + privacy extensions |
| Consensus | PoW (SHA-256d, RandomX, or custom) | PoS (Gasper-like, Tendermint) | PoW (RandomX or custom ASIC-resistant) |
| Signatures | Schnorr (secp256k1) | ECDSA (secp256k1) or BLS | Ring signatures (secp256k1) + Bulletproofs |
| Networking | P2P gossip, compact blocks | devp2p / libp2p | P2P with Dandelion++ |
| Wallet | HD (BIP-32/39), descriptors, PSBT | HD, mnemonic, EIP-712 signing | View key + spend key, subaddresses |
| Explorer | Electrum server + Esplora | The Graph / Ponder / custom | None (privacy) or view-key-based |

### Launch checklist — before mainnet

> **FOR SMART CONTRACTS / TOKENS**
> Code audited by at least one reputable firm, findings resolved. Testnet-deployed and exercised under realistic conditions. Exact compiler version pinned (e.g., `pragma solidity 0.8.37;`, never floating pragmas). Optimizer settings recorded. Deterministic build reproducible. Constructor arguments verified. Source verified on the block explorer. Ownership transferred to a multisig (Safe) + timelock, never an EOA. Initializers called and locked. Pause mechanism tested. Monitoring live (Forta/Defender or custom). Incident runbook written before launch. Bug bounty listed (Immunefi). Events emitted generously (they are your API to the off-chain world).

> **FOR A NEW BLOCKCHAIN**
> All of the above, plus: consensus mechanism tested under adversarial conditions (byzantine nodes, network partitions, double-spend attempts). Multi-client testing if you have more than one implementation (client bugs caused chain splits in Bitcoin and Ethereum history). Testnet running for months with public participation. Difficulty adjustment or staking parameters validated against simulations. Genesis block carefully constructed (no accidental pre-mines, no vulnerable initial distribution). Peer discovery robust. Block propagation time measured and acceptable. Wallet software tested across platforms. Block explorer operational. Documentation complete. A plan for exchange listings (if desired). Legal review of token distribution (securities law varies by jurisdiction). A community of miners/validators ready to secure the network at launch.

> **COMMON FATAL MISTAKES**
> Launching without an audit. Using floating pragma (your deployed bytecode depends on whoever compiled it). Putting an EOA as the contract owner. Blind-signing transactions. Reusing addresses on a privacy chain. Assuming a contract safe on one EVM chain is safe on another. Letting users list arbitrary tokens. Reading a DEX spot price as an oracle. Using `tx.origin` for authorization. Unbounded loops. Storing keys in code or CI. Launching with a tiny security budget on a PoW chain. Ignoring the regulatory landscape. Promising features you haven't built. **All of these have caused real, expensive losses.**

### Glossary

The two sections below are back matter of the source document, following Part X; they are carried here because this is the closing skill of the set.

- **Block** — A container of transactions with a header linking to the previous block, a Merkle root of transactions, and a proof of work (or proof of stake attestation).
- **Coinbase Transaction** — The first transaction in a block, which creates new coins from nothing (the block subsidy plus fees). The only way new coins enter circulation in a PoW system.
- **Consensus** — The mechanism by which nodes agree on the next block and the current state. PoW, PoS, and BFT are the main families.
- **Difficulty** — The PoW target — how hard it is to find a valid block hash. Adjusted periodically to maintain the target block interval.
- **ECDSA** — Elliptic Curve Digital Signature Algorithm. The signature scheme used by Bitcoin (pre-Taproot) and Ethereum. Requires a per-signature random nonce `k` — reuse reveals the private key.
- **EVM** — Ethereum Virtual Machine. A stack-based virtual machine with 256-bit words that executes smart contracts. The de facto standard for smart contract execution.
- **Finality** — When a block is considered permanently part of the chain. Probabilistic (PoW: more confirmations = higher confidence) or explicit (PoS/BFT: a protocol rule that marks a block as final).
- **Fork** — A divergence in the chain. Can be accidental (two miners find blocks simultaneously — resolved by the fork-choice rule) or intentional (a protocol upgrade — requires all nodes to upgrade).
- **Gas** — A unit of computation cost in the EVM. Every operation has a gas cost; every transaction has a gas limit. Gas is a security parameter — it prevents unbounded computation from locking the chain.
- **Genesis Block** — The first block in a blockchain. Has no previous block reference. Its contents (initial coin distribution, initial state) are defined by the protocol designers.
- **Merkle Tree** — A binary tree of hashes enabling compact proofs of inclusion. The root hash commits to the entire dataset; a Merkle proof (O(log n) sibling hashes) proves a specific element is included.
- **Mempool** — Each node's local pool of valid but unconfirmed transactions. Not shared state — each node has its own, and they can differ based on relay policy.
- **Nonce** — In PoW: the value miners grind to find a valid block hash. In ECDSA: the per-signature random value (reuse reveals the private key). In account-model transactions: a counter preventing replay.
- **Pedersen Commitment** — A cryptographic commitment to a value that hides the value but allows verification that inputs equal outputs. Used in confidential transactions.
- **Ring Signature** — A signature where the actual signer is hidden among a group of possible signers. The key privacy primitive for anonymous transaction senders.
- **Schnorr Signature** — A deterministic signature scheme (no nonce hazard) that is linear and aggregatable. Used by Bitcoin's Taproot. An excellent default for new cryptocurrency designs.
- **Slashing** — In PoS, the destruction of a validator's stake for provable misbehavior (double-signing, equivocation). The enforcement mechanism that makes PoS secure.
- **Stealth Address** — A one-time derived address that only the recipient can recognize as theirs, preventing on-chain linkage of payments to the same recipient.
- **Sybil Resistance** — The mechanism that prevents an attacker from creating many fake identities to take over the network. PoW: energy cost. PoS: capital cost. Without it, a single attacker could create millions of nodes and control the network.
- **UTXO** — Unspent Transaction Output. The atomic unit of a Bitcoin-style ledger. Each UTXO is locked by a script and can only be spent by providing a valid unlocking script.

### Further reading

- **Bitcoin** — Andreas Antonopoulos & Steve Harding, *Mastering Bitcoin* (3rd edition), the definitive technical reference. The BIPs repository (bips.dev). Bitcoin Optech newsletter archive. Bitcoin Core source code and documentation.
- **Ethereum** — Andreas Antonopoulos & Gavin Wood, *Mastering Ethereum*. The Ethereum execution and consensus specs. EIPs (eips.ethereum.org). The Foundry Book. The Solidity documentation and security considerations page. OpenZeppelin Contracts documentation. The RareSkills blog for deep mechanics.
- **Monero** — SerHack, *Mastering Monero* (free). getmonero.org developer guides. Monero Research Lab papers. The FCMP++/CARROT specification repositories.
- **Cryptography** — Bruce Schneier, *Applied Cryptography*. Dan Boneh & Victor Shoup, *A Graduate Course in Applied Cryptography* (free online). The libsodium documentation. NIST post-quantum cryptography standards.
- **Distributed systems** — Leslie Lamport, Robert Shostak, Marshall Pease, "The Byzantine Generals Problem" (1982), the original paper that defines the fundamental problem all consensus mechanisms solve. Satoshi Nakamoto, "Bitcoin: A Peer-to-Peer Electronic Cash System" (2008) — the paper that launched everything, and is still worth reading carefully.
