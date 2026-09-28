---
id: skill-4-sequenced-study-roadmap-8-serious-weeks-0b3db809b7
purpose: 4 sequenced study roadmap 8 serious weeks
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-choosing-a-rail-and-shared-patterns/SKILL.md
requires: ["skill-3-the-four-engineering-patterns-that-transfer-everywhere-78ed7c0d95"]
links: ["skill-5-canonical-documentation-shelf-61bccdf9da"]
---

## 4. Sequenced study roadmap (≈8 serious weeks)

**Weeks 1–2 — foundations**: UTXO vs account models; PoW/PoS; keys, seeds, BIP-39/HD derivation; the payment lifecycle (auth/capture/settle/refund); PCI scope. *Build*: a regtest wallet flow with `bitcoin-cli`; a Stripe test-mode PaymentIntent end-to-end incl. webhook.
**Weeks 3–4 — crypto depth**: Ethereum EVM + gas + storage; write/compile/test a contract in Foundry; run the exploit list against toy contracts (reentrancy, oracle, access control); Lightning: open channels on signet, pay a BOLT11 invoice, resize via splicing on CLN. Monero: run `monerod` on stagenet, subaddress per counterparty, produce and verify a tx proof.
**Weeks 5–6 — fiat depth**: subscriptions with test clocks + dunning; a Connect Express pilot; tax engine integration; write the reconciliation job (Stripe balance transactions vs. your ledger). Read one PCI v4.0.1 SAQ end to end.
**Week 7 — cross-cutting**: GENIUS/MiCA/AMLR text-level reading; the v30/v31 Bitcoin release notes as governance case study; FCMP++ spec skimming; L2Beat stage model.
**Week 8 — capstone build** (one): a paid-API product accepting Stripe + stablecoins; or a self-custodial donation page (BTCPay-style on signet/testnets); or an escrow-style PSBT multisig tool.
