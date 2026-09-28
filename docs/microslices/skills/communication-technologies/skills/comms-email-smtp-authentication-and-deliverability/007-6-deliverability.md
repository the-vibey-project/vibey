---
id: skill-6-deliverability-9647d54f44
purpose: 6 deliverability
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-email-smtp-authentication-and-deliverability/SKILL.md
requires: ["skill-5-spf-dkim-dmarc-d6bab0af3e"]
links: ["skill-7-email-encryption-3fd1dda0aa"]
---

## §6. ⚠️ Deliverability

**⚠️ Getting mail accepted is a different problem from sending it**, ⚠️ **and it is
governed by reputation rather than by rules.**
**⚠️ What actually determines it**: ⚠️ **sending IP and domain reputation, authentication
(§5), ⚠️ ENGAGEMENT SIGNALS (opens, replies, and especially deletions-without-reading),
complaint rate, spam-trap hits, list hygiene, and consistency of volume.**
> **⚠️ GOTCHA — complaint rate is the metric that kills you, and the thresholds are
> brutally low.** ⚠️ **Major providers publish complaint-rate targets in the region of a
> tenth of a percent — meaning a handful of "report spam" clicks per thousand messages is
> enough to damage a sending reputation.** **⚠️ One easy unsubscribe link prevents more
> deliverability damage than any amount of content tuning.**

**⚠️ Bulk sender requirements** now enforced by the large providers require ⚠️ **SPF, DKIM,
DMARC, one-click unsubscribe and complaint-rate limits — which formalized what was
previously informal.**
**⚠️ Shared versus dedicated IPs, warming, and subdomain separation** (⚠️ **transactional
mail on a different subdomain from marketing, so a bad campaign cannot take down your
password resets**).
**⚠️ The uncomfortable structural point**: ⚠️ **a handful of providers effectively decide
whose email is delivered, with no appeal — which is centralization arriving at a federated
system through the back door** (§1).

---
