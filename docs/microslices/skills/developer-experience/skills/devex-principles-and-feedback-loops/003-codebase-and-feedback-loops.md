---
id: skill-codebase-and-feedback-loops-d9fa706dc1
purpose: codebase and feedback loops
source: src/vibey_tools/skills/plugins/developer-experience/skills/devex-principles-and-feedback-loops/SKILL.md
requires: ["skill-evidence-base-339b8b7252"]
links: []
---

## Codebase and feedback loops

Code quality and loop speed are the two levers with the best support; everything here serves them.

**Structure**

- Keep one obvious entry point per concern, with module names that match the domain vocabulary used in docs and errors.
- Prefer small, boring, consistently formatted code; enforce style with an autoformatter so review never debates it.
- Put architecture decisions in short records (ADRs) so "why" survives staff turnover.
- Keep the public surface small; mark internals private so autocomplete shows only supported choices.

**Local setup**

- One command to a working environment (a reproducible shell such as Devbox, a dev container, or a documented `make setup`). Local setup is the top newcomer barrier in the OSS literature.
- Seed data and sample config included; secrets via a documented dev-only path.
- A `doctor` command that checks versions, ports and credentials and says how to fix each failure.

**Build, test, review**

- Track median and tail latency for build, test and CI separately; predictability matters as much as the median.
- Fast tests run by default; slow suites are opt-in and parallelized. Quarantine flaky tests quickly, because they erode trust in every red build (the commonly quoted figures are secondary-sourced).
- Pre-commit hooks stay under a few seconds; heavy checks move to CI.
- Small pull requests, a review-turnaround target, and clear ownership files keep review from becoming the queue everyone waits in.
- CI failures link to the exact log line and a one-line reproduction command.
