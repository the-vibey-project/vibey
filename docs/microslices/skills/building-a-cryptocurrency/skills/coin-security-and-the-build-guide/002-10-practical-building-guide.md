---
id: skill-10-practical-building-guide-200a436140
purpose: 10 practical building guide
source: src/vibey_tools/skills/plugins/building-a-cryptocurrency/skills/coin-security-and-the-build-guide/SKILL.md
requires: ["skill-9-security-what-actually-loses-money-15b470d80e"]
links: []
---

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
    uint256 public constant TOTAL_SUPPLY = 100_000_000 * 10**18; // 100M tokens

    struct VestingSchedule {
        uint256 totalAmount;
        uint256 claimed;
        uint256 startTimestamp;
        uint256 durationSeconds;
    }

    mapping(address => VestingSchedule) public vesting;

    /// @notice Tokens promised to beneficiaries and not yet paid out. Every
    /// schedule adds to it; every claim subtracts from it. The contract's
    /// balance minus this is what the owner is still free to promise.
    uint256 public totalReserved;

    event VestingSet(address indexed beneficiary, uint256 amount, uint256 durationSeconds);
    event VestingClaimed(address indexed beneficiary, uint256 amount);

    constructor() ERC20("MyCoin", "MYC") Ownable(msg.sender) {
        _mint(address(this), TOTAL_SUPPLY);
    }

    /// @notice Set vesting for a team member or investor
    function setVesting(address beneficiary, uint256 amount, uint256 duration)
        external
        onlyOwner
    {
        require(beneficiary != address(0), "Zero beneficiary");
        require(amount > 0, "Zero amount");
        require(duration > 0, "Zero duration");
        require(vesting[beneficiary].totalAmount == 0, "Already vested");
        // Check against the UNRESERVED balance. The raw balance still holds every
        // token already promised to someone else.
        require(amount <= balanceOf(address(this)) - totalReserved, "Insufficient unreserved balance");
        totalReserved += amount;
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
        // Clamp. Past the end of the schedule the whole allocation is vested and
        // not one token more.
        if (elapsed > v.durationSeconds) {
            elapsed = v.durationSeconds;
        }
        uint256 vested = (v.totalAmount * elapsed) / v.durationSeconds;
        uint256 claimable = vested - v.claimed;
        require(claimable > 0, "Nothing to claim");
        v.claimed += claimable;
        totalReserved -= claimable;
        emit VestingClaimed(msg.sender, claimable);
        _transfer(address(this), msg.sender, claimable);
    }
}
```

> **STATUS OF THIS LISTING: RECONSTRUCTED AND HAND-CHECKED, NOT MACHINE-COMPILED**
>
> Four lines are clipped at the right margin in the source document — the `TOTAL_SUPPLY` comment,
> the `VestingSet` event signature, the `setVesting` signature, and the trailing semicolon of the
> balance `require` — and the source's vesting logic carries the two bugs described below. What is
> printed above is therefore **reconstructed**: the clipped lines restored, the two bugs fixed,
> because the recipe that follows tells you to write and deploy this contract and a damaged listing
> is not one you can deploy.
>
> **It has been read line by line. It has not been through `solc`.** No compiler, no test suite and
> no audit has seen it, here or anywhere. Treat it as a **starting point to compile, test and
> audit** — not as something to deploy, and not as evidence that any particular Solidity version or
> OpenZeppelin release accepts it as written.

> **TWO BUGS IN THE SOURCE'S VESTING, FIXED ABOVE**
>
> **It over-allocated.** The source checked each new schedule against the contract's *current
> balance*. That balance still holds every token already promised to every other beneficiary, so an
> owner can write schedules that each fit and together do not — and the beneficiary who claims last
> finds the contract empty and their transaction reverting. Reserving is the fix: `totalReserved`
> goes up on `setVesting`, down on each claim, and a new schedule is checked against
> `balanceOf(address(this)) - totalReserved`.
>
> **It paid past the end of the schedule.** The source computed `vested = totalAmount * elapsed /
> durationSeconds` with nothing bounding `elapsed`. One duration after the start `vested` equals
> `totalAmount`, which is right; two durations after, the arithmetic claims twice the allocation,
> paid out of other beneficiaries' tokens. Clamping `elapsed` to `durationSeconds` before the
> division is the whole fix.
>
> Both are ordinary logic errors — the ~$64M category in the table above, not exotic cryptography —
> and both are exactly what invariant testing catches. Assert, as invariants: the sum over all
> schedules of `totalAmount - claimed` never exceeds `balanceOf(address(this))`, and no beneficiary
> can ever be paid more than their `totalAmount`.

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
| Signatures | Schnorr (secp256k1) | ECDSA (secp256k1) or BLS | Linkable ring signatures over Ed25519 — an Edwards-form Curve25519, **not** secp256k1 — with Bulletproofs+ range proofs on the amounts |
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
- **Coinbase Transaction** — The first transaction in a block. It has one special input whose previous-output reference is null, and its outputs pay the block subsidy plus the fees collected from the block's other transactions. Only the subsidy is newly created in this transaction; the fees already existed as inputs elsewhere in the block. On a Bitcoin-style chain after genesis with subsidy-only issuance, the subsidy is the only ongoing issuance path.
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
- **Schnorr Signature** — A linear, aggregatable signature scheme, used by Bitcoin's Taproot and the basis of MuSig2 multisig. Still nonce-based: BIP340 specifies a deterministic nonce derivation, but that is a construction choice, and a repeated or biased nonce reveals the private key exactly as it does in ECDSA. An excellent default for new designs — provided the nonce derivation is the specified one.
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
