---
id: skill-4-the-payment-system-taxonomy-d6abd02f7b
purpose: 4 the payment system taxonomy
source: src/vibey_tools/skills/plugins/banking-swift-and-payment-networks/skills/banking-payments-banks-reserves-and-settlement/SKILL.md
requires: ["skill-3-central-banks-and-reserves-93cdef7644"]
links: ["skill-5-clearing-netting-and-settlement-risk-2fd7a7e9dc"]
---

## §4. The Payment System Taxonomy

```
⚠️ ⚠️ RTGS (Real-Time Gross Settlement)  ⚠️ each payment settled
   INDIVIDUALLY and IMMEDIATELY in central bank money.
   ⚠️ No settlement risk; ⚠️ HIGH LIQUIDITY DEMAND, because you
   need the full amount at the moment of payment
   ⚠️ Fedwire, TARGET2/T2, CHAPS
⚠️ ⚠️ DEFERRED NET SETTLEMENT  ⚠️ obligations accumulate and are
   NETTED, settling once or a few times a day.
   ⚠️ Hugely liquidity-efficient; ⚠️ carries settlement risk
   between netting cycles
   ⚠️ ACH, BACS, most retail systems
⚠️ ⚠️ HYBRID  ⚠️ most modern large-value systems, with liquidity-
   saving mechanisms that offset queued payments against each
   other while retaining gross finality. ⚠️ CHIPS is the classic
⚠️ INSTANT / FAST PAYMENT  ⚠️ 24/7, near-real-time, retail-scale,
   with finality in seconds (§17)
⚠️ CARD NETWORKS  ⚠️ a DIFFERENT ANIMAL — authorization is
   near-instant, ⚠️ but clearing and settlement happen later,
   which is why a "pending" charge can vanish
⚠️ SECURITIES SETTLEMENT  ⚠️ DVP (delivery versus payment) links
   the asset leg to the cash leg so neither can happen alone —
   the same idea as PVP for FX (§5)
```

---
