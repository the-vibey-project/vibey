---
id: skill-measurement-and-launch-checklist-62a27cbbe2
purpose: measurement and launch checklist
source: src/vibey_tools/skills/plugins/developer-experience/skills/devex-reference/SKILL.md
requires: []
links: ["skill-where-the-evidence-is-weak-or-conflicting-09e0c9d019"]
---

## Measurement and launch checklist

Pair what developers say with what systems record, and choose one North Star per team.

| Dimension | Perception (survey) | Workflow (system data) |
| --- | --- | --- |
| Feedback loops | Satisfaction with build, test and review speed | Build, test, CI and review-turnaround times (median and tail) |
| Cognitive load | "How hard is it to understand this code?" | Time to first successful call; onboarding duration |
| Flow state | Focus time and interruptions | Meeting load; context switches |
| Reliability | Trust in tests and tooling | Flaky-test rate; failed-build rate |

**Launch checklist**

- [ ] Fresh-machine setup finishes with one command and is timed
- [ ] Every command has examples in `--help`, `--json` where useful, and documented exit codes
- [ ] Every error has a location, a cause, a fix and a stable code
- [ ] README runs end to end and doc examples are tested in CI
- [ ] Public API names reviewed for consistency; deprecation policy published
- [ ] AGENTS.md and an llms.txt exist, and MCP tool count is justified
- [ ] Telemetry is opt-in, disclosed and honors `DO_NOT_TRACK`
- [ ] Accessibility checked with a screen reader and keyboard only
- [ ] A quarterly DevEx survey and a named owner exist

The doc is general because no repository was supplied; an audit of your actual codebase, CLI and docs against this checklist is the natural next step.
