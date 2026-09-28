---
id: skill-22-what-doesn-t-transfer-honestly-a19c25489f
purpose: 22 what doesn t transfer honestly
source: src/vibey_tools/skills/plugins/civil-industrial-engineering-for-software-devs/skills/civil-reliability-safety-and-what-transfers-to-software/SKILL.md
requires: ["skill-21-what-transfers-well-f20e862ea2"]
links: []
---

## §22. ⚠️ What Doesn't Transfer — Honestly

> **⚠️ This section exists because the "be more like real engineers" argument is usually
> made without engaging the disanalogies, and the disanalogies are real.**

```
⚠️ 1. NO MATERIAL PROPERTIES. There is no characteristic strength of code,
   no distribution to apply a partial factor to (§3). Factor-of-safety
   reasoning has no direct numerical analogue
⚠️ 2. REQUIREMENTS CHANGE DURING CONSTRUCTION. A building's programme is
   largely fixed at design; software's is not, and pretending otherwise
   is what waterfall was. ⚠️ This is a genuine categorical difference
⚠️ 3. ZERO MARGINAL COST OF REPLICATION AND CHANGE. ⚠️ You cannot rebuild a
   bridge to try an idea; you can redeploy software in minutes. ⚠️ This
   INVERTS the economics of upfront design — cheap iteration is
   rationally preferable where it's available, and civil engineering
   front-loads precisely because it isn't
⚠️ 4. ADVERSARIAL LOADS. Gravity does not adapt to your design. Attackers
   do. ⚠️ No civil analogue exists for an intelligent adversary
   searching for your weakest assumption
⚠️ 5. NO STABLE SUBSTRATE. Steel's properties don't change annually.
   ⚠️ Your language, framework, cloud and OS all do (§6)
⚠️ 6. INVISIBLE, UNINSPECTABLE ARTEFACT. A third party can inspect
   rebar placement. ⚠️ Nobody can inspect a codebase to the same standard,
   which is why the code-and-permit model doesn't port (§6)
⚠️ 7. NON-REPETITIVE WORK. Work measurement and Six Sigma assume repeated
   processes; software development is not one (§15, §16)
```
**⚠️ The one that cuts the other way, and should be conceded**: ⚠️ **the accountability
structure (§7 → `civil-codes-licensure-failure-analysis-and-construction`) is a genuine difference and NOT explained away by any of the above.**
**An individual who personally loses their licence behaves differently under commercial
pressure than an employee who can be overruled.** ⚠️ **Software's absence of that structure
is a choice the industry has made, not a technical necessity** — **and regulated software
domains demonstrate it's possible when the consequences justify the cost.**
**⚠️ The synthesis I'd offer**: ⚠️ **software should stop borrowing civil engineering's
CULTURE (upfront design, formal ceremony, credentialism) and start borrowing industrial
engineering's MATHEMATICS and safety engineering's INSTITUTIONS.** **The first is a poor
fit for the reasons above; the second two fit exactly.**
