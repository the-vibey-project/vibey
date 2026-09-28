---
id: skill-8-measurement-and-attribution-ef43132267
purpose: 8 measurement and attribution
source: src/vibey_tools/skills/plugins/business-marketing-sales-law/skills/biz-marketing-evidence-brand-and-attribution/SKILL.md
requires: ["skill-7-brand-and-advertising-3866cef073"]
links: ["skill-9-channels-4a6b813015"]
---

## §8. ⚠️ Measurement and Attribution

**⚠️ The central fact: attribution is modeled, not observed.** **Nobody sees the
counterfactual — what would have happened without the ad — and every attribution model is
an assumption about it.**

```
LAST CLICK       ⚠️ gives all credit to the final touch. Systematically over-credits
                 search and retargeting, which harvest demand they didn't create
FIRST CLICK      the mirror error
MULTI-TOUCH (MTA) ⚠️ fractional credit across touchpoints. Needs user-level tracking (§22.1)
MMM              ⚠️ aggregate regression of outcomes on spend. No personal data needed
INCREMENTALITY   ⚠️ holdout/geo experiments. THE ONLY method that measures causation
```
> **⚠️ GOTCHA — platform-reported conversions are marketing, not measurement.** ⚠️ **Every
> ad platform marks its own homework, and they double-count each other: sum your platform
> dashboards and you will typically exceed your actual revenue.** **Reported figures for
> modeled conversions can over-report substantially versus holdout tests.**
> ⚠️ **The only defensible reconciliation is a holdout experiment**, and the practitioner
> answer is triangulation — **use incrementality to calibrate how much to discount each
> platform's numbers, MMM for budget allocation, and platform data only for in-channel
> tuning.**

**⚠️ Retargeting deserves specific scepticism**: **it targets people already intending to
buy, so last-click attribution credits it enormously and incrementality tests routinely
find much smaller true lift.** **It's the canonical example of measuring harvest as if it
were cultivation.**

---
