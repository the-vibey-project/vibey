---
id: skill-common-metrics-anti-patterns-181b0db09f
purpose: common metrics anti patterns
source: src/vibey_tools/skills/plugins/agile-delivery/skills/engineering-metrics/SKILL.md
requires: ["skill-presenting-metrics-to-leadership-90e72d6051"]
links: ["skill-using-metrics-to-identify-systemic-problems-not-blame-61171d686b"]
---

## Common Metrics Anti-Patterns

### Story Points as Productivity Metrics
**What goes wrong:** Teams inflate estimates, cherry-pick easy work, sacrifice quality for point counts. Comparing points across teams is meaningless — each team's estimates reflect unique domain complexity.

**Correct use:** Story points are team-internal planning tools for forecasting sprint capacity. Never a target, never compared across teams.

### Lines of Code
**What goes wrong:** Incentivizes verbose code; penalizes refactoring; rewards copy-paste over abstraction.

**Never use.** Not even directionally useful.

### Utilization Rate
**What goes wrong:** 100% utilization in a variable system causes cycle time to explode exponentially (Little's Law). Teams at 100% utilization have no capacity to handle surprises, help teammates, or improve processes.

**Target 80–85% utilization** to maintain flow efficiency. 15–20% slack is productive capacity, not waste.

### Coverage as a Target
**What goes wrong:** 100% coverage targets are gamed — trivial tests that don't validate behavior get written to hit the number. Teams pass coverage while having brittle, meaningless test suites.

**Correct use:** Coverage is a **floor** (minimum acceptable level), not a goal. Set a minimum threshold (e.g., 80%), track coverage deltas on PRs to prevent regression, and focus test investment on **critical paths** (authentication, data access, payment flows) rather than overall percentage.

### Velocity as Performance Target
**What goes wrong:** Goodhart's Law applies mercilessly. When velocity becomes a target, teams inflate estimates, cherry-pick easy work, and sacrifice quality for throughput. Comparing velocity across teams is meaningless.

**Correct use:** Velocity is a team-internal planning tool for sprint forecasting only. If velocity is declining, investigate why — but do not treat it as a performance problem in isolation.

### Single Metric Dashboard
**What goes wrong:** Any single metric can be optimized at the expense of everything else. Maximizing deployment frequency without maintaining change failure rate produces frequent broken deployments.

**Correct use:** Always use the DORA four together as a balanced set. Add SPACE dimensions to prevent gaming the DORA metrics.

---
