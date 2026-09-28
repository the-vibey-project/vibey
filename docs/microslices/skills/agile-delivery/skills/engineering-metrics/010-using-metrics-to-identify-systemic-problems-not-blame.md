---
id: skill-using-metrics-to-identify-systemic-problems-not-blame-61171d686b
purpose: using metrics to identify systemic problems not blame
source: src/vibey_tools/skills/plugins/agile-delivery/skills/engineering-metrics/SKILL.md
requires: ["skill-common-metrics-anti-patterns-181b0db09f"]
links: ["skill-reliability-as-the-fifth-dora-metric-7c66b5facd"]
---

## Using Metrics to Identify Systemic Problems (Not Blame)

### The Principle
Metrics should reveal **system problems**, not surface **individual failures**. The system produces the outcomes; individuals operate within the system. This mirrors Amy Edmondson's psychological safety research and Google SRE's blameless postmortem model.

### Investigation Pattern

When a metric deteriorates:
1. **Observe the trend** — is this one sprint or a sustained pattern?
2. **Hypothesize system causes** — what in the process, tooling, or architecture could produce this outcome?
3. **Test the hypothesis** — gather supporting data before drawing conclusions
4. **Identify the leverage point** — where in the system can one change produce the most improvement?
5. **Create an improvement story** — add a Backlog item; own the fix as a team

Example: Change Failure Rate increases over 3 sprints.
- Not: "The engineers are writing worse code"
- Investigate: Did test coverage drop? Was there a new area of the codebase with no integration tests? Did PR review thoroughness decrease (review turnaround time data)?
- Finding: New microservice was added with no contract tests; it fails when the provider changes its API
- Fix: Add Pact contract testing for this service; add to Definition of Done for new service creation

---
