---
id: skill-6-time-handling-b541e8aed2
purpose: 6 time handling
source: src/vibey_tools/skills/plugins/reporting-and-dashboards/skills/reporting-semantic-layer-time-and-performance/SKILL.md
requires: ["skill-5-the-semantic-layer-d355433096"]
links: ["skill-7-query-performance-ddc69f6aec"]
---

## §6. ⚠️ Time Handling

**⚠️ Time is where reporting bugs breed, and every item here has bitten real teams.**

**Timezones:**
- **⚠️ Store UTC, convert at presentation.** **Non-negotiable.**
- ⚠️ **But "daily revenue" is a business question with a timezone answer.** **Whose
  midnight?** **A US retailer reporting in UTC will have days that don't match the store's
  day, and the numbers will never reconcile to the POS system.**
- **⚠️ DST means some local days have 23 or 25 hours.** **Hourly comparisons across a DST
  boundary are not like-for-like, and one hour either repeats or doesn't exist.**

**⚠️ Calendars**: **fiscal years often don't start in January**; **4-4-5 retail calendars**
(⚠️ **so that comparable periods have the same number of weekends — and week-over-week
comparison in a 4-4-5 calendar is not the same as ISO weeks**); **ISO weeks** (⚠️ **week 1
contains the first Thursday, so early January can be week 52 of the previous year — a
genuine source of off-by-one-year bugs**).

**⚠️ Build a date dimension table.** One row per day with fiscal period, ISO week, holiday
flags, day-of-week, and relative offsets. ⚠️ **It's trivially cheap and it removes an
entire class of date-arithmetic bugs from every query downstream.**

> **⚠️ GOTCHA — partial periods are the most common dashboard lie.** ⚠️ **A
> "month-to-date vs last month" comparison on the 8th compares 8 days against 30, and it
> will look like catastrophe.** **Either compare like-for-like (MTD vs same-period-last-
> month), or label the partial period unmistakably.** **The number of executives who have
> been alarmed by a partial-period chart is not small.**

**⚠️ Late-arriving data** — **events land after the period closed.** **A dashboard read on
Monday and again on Wednesday shows different numbers for the same past day**, which
⚠️ **destroys trust faster than almost anything else.** **The fixes: a stated data-
completeness window, restating periods explicitly, or showing an "as of" watermark.**
**⚠️ Say which one you're doing, visibly.**

**Also**: **event time vs processing time**, **backfills after logic changes** (⚠️ **and
whether historical numbers are allowed to change is a policy decision, not a technical
one**), **and slowly changing dimension timing** (§2 → `reporting-architecture-modelling-and-aggregation-traps`).

---
