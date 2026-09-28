---
id: skill-part-14-customer-issue-triage-e857987992
purpose: part 14 customer issue triage
source: src/vibey_tools/skills/plugins/quality-engineering/skills/debugging-and-observability/SKILL.md
requires: ["skill-part-13-testing-for-debuggability-66932570f0"]
links: ["skill-part-15-observability-2-0-23a0133a38"]
---

## Part 14 — Customer Issue Triage

### Bug Report Requirements

A good bug report captures: steps to reproduce, expected vs. actual behavior, environment, frequency, severity, business impact, customer screenshots/logs.

**Triage questions:** All users or some? Did something change? Is there a workaround? What is the urgency?

### Severity Classification (Industry-Standard)

| Priority | Meaning |
|----------|---------|
| P0 | Production down |
| P1 | Major feature broken |
| P2 | Workaround exists |
| P3 | Minor |
| P4 | Enhancement |

SLA turnaround scales with severity. The "can we reproduce it?" gate drives prioritization.

### Root Cause Analysis

**Five Whys** (Toyota/Ohno) — drills from symptom to systemic cause. Known limitation: assumes a single linear causal chain. Complex software systems fail through **networks of contributing conditions**, not single root causes.

Complementary techniques:
- **Fishbone/Ishikawa** — categorize causes
- **Fault Tree Analysis** — top-down deductive
- **FMEA** — proactive risk assessment
- **Change analysis** — correlate the bug's appearance with recent code/config/infra/data changes (usually the fastest path to a "smoking gun")

Avoid "fix the symptom not the cause" — verify the proposed root cause explains *all* observed symptoms.

### Fix, Test, Prevent

1. Write a failing regression test *before* fixing (TDD fix discipline)
2. Decide minimal patch vs. refactor
3. Verify in production via canary + monitoring + customer confirmation
4. Address the systemic cause: add observability, validation, error handling, tests
5. Maintain a blameless culture

---
