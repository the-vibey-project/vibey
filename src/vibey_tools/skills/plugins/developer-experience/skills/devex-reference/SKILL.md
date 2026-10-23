---
name: devex-reference
description: "Use when measuring developer experience (perception surveys paired with system data, one North Star per team), running the launch checklist before shipping a developer tool, checking which developer-experience claims are weak or contested (Diataxis, DX Core 4, the 23-minute interruption figure, flaky-test statistics, the METR AI trial, AGENTS.md adoption counts), or finding the primary sources. Triggers on DevEx survey, DORA, SPACE, DX Core 4, developer productivity metrics, METR study, launch checklist, evidence grade. Companion to the other developer-experience skills."
---

# Developer Experience: Measurement, Launch Checklist, Weak Evidence, and Sources

> **Part 5 of 5** of the *Developer Experience Blueprint* (plugin `developer-experience`), covering: Measurement and launch checklist; Where the evidence is weak or conflicting; Sources. Sibling skills: `devex-principles-and-feedback-loops`, `devex-cli-and-errors`, `devex-api-sdk-and-docs`, `devex-interfaces-onboarding-and-agents`. A reference into a sibling is written *Section name → `skill`*.
>
> **Currency:** the blueprint is dated Oct 23, 2026; its evidence base and the AI-tooling claims age fastest, so re-check those first.
>
> Evidence grades used throughout: **A** = peer-reviewed or large study, **B** = credible practitioner or single study, **C** = vendor or opinion. Thin evidence is flagged where it occurs, and collected under *Where the evidence is weak or conflicting* in `devex-reference`.

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

## Where the evidence is weak or conflicting

- **Diátaxis:** read only through secondary sources; the official site was not retrieved.
- **DX Core 4:** vendor-affiliated, so its figures are marketing-adjacent until independently replicated.
- **Interruption recovery:** the widely repeated \~23 minutes comes from Mark's work; another paper reports about 25 minutes 26 seconds, and the return interval includes other productive work, so treat it as order-of-magnitude.
- **Flaky-test trust erosion:** the numbers are secondary-sourced.
- **AGENTS.md adoption:** counts conflict (20,000+ versus 60,000+).
- **METR trial:** small sample and a narrow setting; it does not show that AI slows all developers.
- **LLM-enhanced error messages:** ineffective in one study only.
- **CLI screen-reader finding:** checked from an abstract and a summary, not the full paper.
- **Agent-friendly CLI patterns and llms.txt:** practitioner evidence only.

## Sources

- [DevEx: What Actually Drives Productivity (ACM Queue)](https://queue.acm.org/detail.cfm?id=3595878)
- [METR early-2025 AI and experienced open-source developers study](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/)
- [DX newsletter: build times and developer productivity](https://newsletter.getdx.com/p/build-times-and-developer-productivity)
- [Steinmacher et al., barriers faced by OSS newcomers](https://www.ime.usp.br/~gerosa/papers/08254320.pdf)
- [Compiler error messages considered unhelpful (summary)](https://neverworkintheory.org/2021/09/02/compiler-error-messages-considered-unhelpful.html)
- [Rust compiler development guide: diagnostics](https://rustc-dev-guide.rust-lang.org/diagnostics.html)
- [Command Line Interface Guidelines](https://github.com/cli-guidelines/cli-guidelines) and a [condensed copy](https://cdn.jsdelivr.net/npm/@hacxy/skills@0.1.0/skills/create-cli/references/cli-guidelines.md)
- [NO\_COLOR](https://no-color.org)
- [Stripe: API versioning](https://stripe.com/blog/api-versioning)
- [Nordic APIs: time to first call](https://nordicapis.com/why-time-to-first-call-is-a-vital-api-metric/)
- [Cloudinary llms.txt (example)](https://cloudinary.com/documentation/llms.txt)

Studies cited by name without a link (Myers & Stylos, Robillard & DeLine, Fagerholm & Münch, Greiler/Storey/Noda, SPACE, Mark) were recalled from earlier reading in this session and not re-opened for the final doc.
