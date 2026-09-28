---
id: skill-test-strategy-document-one-page-template-2416aa5af8
purpose: test strategy document one page template
source: src/vibey_tools/skills/plugins/quality-engineering/skills/test-strategy/SKILL.md
requires: ["skill-assessing-test-suite-health-diagnostic-questions-2047556988"]
links: []
---

## Test Strategy Document: One-Page Template

For communicating test strategy to stakeholders:

```
TEST STRATEGY: [System Name]

ARCHITECTURE TYPE: [Monolith / API / Microservices / Frontend]
RECOMMENDED SHAPE: [Pyramid / Trophy / Honeycomb]

TEST DISTRIBUTION TARGET:
  Unit tests:           [X%] — [rationale]
  Integration tests:    [X%] — [rationale]
  Contract tests:       [X%] — [rationale, if microservices]
  E2E tests:            [X%] — [rationale]

QUALITY GATES:
  Coverage threshold:   [80%] overall, [100%] for [list critical paths]
  Flake rate:           < 2% per test
  Full suite runtime:   < [30 min]
  SAST scan:            0 Critical/High findings

RISK COVERAGE (Swiss Cheese):
  ✓ Static analysis (Ruff, mypy, Bandit)
  ✓ Unit tests
  ✓ Integration tests (testcontainers)
  ○ Contract tests [MISSING — see Q3 OKR]
  ✓ E2E tests (smoke tests for critical journeys)
  ✓ Production monitoring (Application Insights alerts)

CURRENT STATE:
  Coverage: [X%] | Flake rate: [X%] | Suite runtime: [Xm]
  Top risk: [e.g., no contract tests for InventoryService boundary]

IMPROVEMENT PRIORITY:
  1. [Highest-impact gap]
  2. [Second priority]
  3. [Third priority]
```
