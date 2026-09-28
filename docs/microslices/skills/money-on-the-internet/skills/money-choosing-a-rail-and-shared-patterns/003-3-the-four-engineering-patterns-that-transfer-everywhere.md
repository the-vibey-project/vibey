---
id: skill-3-the-four-engineering-patterns-that-transfer-everywhere-78ed7c0d95
purpose: 3 the four engineering patterns that transfer everywhere
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-choosing-a-rail-and-shared-patterns/SKILL.md
requires: ["skill-2-decision-heuristics-54ba0e9f84"]
links: ["skill-4-sequenced-study-roadmap-8-serious-weeks-0b3db809b7"]
---

## 3. The four engineering patterns that transfer everywhere

1. **Idempotency keys derived from business attempts, persisted before first call** — Stripe `Idempotency-Key`, PayPal `PayPal-Request-Id`, Bitcoin (txid/RBF discipline), Ethereum (nonce management + "did that tx actually revert?"), Monero (txid + proofs).
2. **Webhooks/events are the source of truth; the UI is a hint** — PSP webhooks (at-least-once, verify, dedupe, re-fetch) ≡ on-chain confirmations (wait for depth, handle reorgs, re-read state).
3. **Append-only ledger beats mutable columns** — double-entry ledger for fiat reconciliation ≡ the blockchain itself. Build the ledger at project start; retrofitting it is misery.
4. **Assume the adversarial input** — on-chain: anyone can call anything; off-chain: anyone can POST to your webhook endpoint or replay a request. Signature verification and state-machine discipline either side.
