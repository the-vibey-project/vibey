---
id: skill-2-the-privacy-stack-durable-356e0ce8a9
purpose: 2 the privacy stack durable
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-monero/SKILL.md
requires: ["skill-1-what-it-is-and-the-honest-trade-421a7d6e77"]
links: ["skill-3-fcmp-the-upgrade-that-matters-and-its-real-status-versioned-verify-before-relying-478518c59d"]
---

## 2. The privacy stack — [DURABLE]

Every transaction uses all of these:

1. **Stealth addresses**: the sender derives a **one-time output address** from the recipient's published address; only the recipient's private **view key** can recognize funds as theirs. An outside observer cannot tell two payments went to the same person. Since *no address is ever reused on-chain*, the "address book" intuition from Bitcoin doesn't exist.
2. **Ring signatures**: each spent input is signed together with **15 decoy outputs pulled from the chain (ring size 16, since the Aug 2022 hard fork)**; the network verifies *one* output was spent without learning which.
3. **RingCT**: amounts are hidden in **Pedersen commitments**; the network verifies inputs + fee = outputs without seeing values.
4. **Bulletproofs+**: compact zero-knowledge range proofs proving committed amounts are non-negative (i.e., no value created from nothing) without revealing them.
5. **Subaddresses**: unlimited unlinkable receive addresses from one wallet seed. *(The older "integrated address" with payment IDs is deprecated — exchanges historically used it for deposit identification; don't build on it.)*
6. **Dandelion++**: transaction broadcast first propagates through a private "stem" phase over peers before flooding, making network-level IP↔tx linkage harder.
7. **RandomX**: a CPU-optimized PoW that keeps mining viable on commodity hardware and ASICs uneconomic — decentralization of *mining* by design.
8. **Dynamic block size + tail emission**: ~2-minute blocks that expand under demand, and after the subsidy curve ended (June 2022) a perpetual **0.6 XMR/block** keeps miners funded forever (~0.87%/yr effective inflation, declining).

The two-key model matters for development: **private view key** (sees incoming payments; shareable for watch-only/audit wallets) and **private spend key** (moves funds). For *outgoing* payments you can prove a specific payment was made with `get_tx_key`/`check_tx_proof` — selective disclosure is possible; the default is just that it's *optional*.

---
