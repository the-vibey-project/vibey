---
id: skill-evidence-base-339b8b7252
purpose: evidence base
source: src/vibey_tools/skills/plugins/developer-experience/skills/devex-principles-and-feedback-loops/SKILL.md
requires: ["skill-principles-639aa30050"]
links: ["skill-codebase-and-feedback-loops-d9fa706dc1"]
---

## Evidence base

The field is young and mixes rigorous studies with vendor surveys, so weigh each source by type.

| Source | What it supports | How far to trust it |
| --- | --- | --- |
| [DevEx, ACM Queue 2023](https://queue.acm.org/detail.cfm?id=3595878) | Feedback loops, cognitive load and flow state as the drivers; measure perception plus workflow | Practitioner-researcher framework; widely used |
| Fagerholm & Münch 2012; Greiler, Storey & Noda (21 interviews) | Definitions and factor lists for DX | Qualitative, small samples |
| SPACE framework | Productivity has several dimensions; no single metric | Conceptual |
| DX Core 4 | A bundled metric set | Vendor-affiliated; treat figures cautiously |
| [METR randomized trial, 2025](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/) | Experienced developers were 19% slower with AI tools in one narrow setting | Small sample, early-2025 tools; do not generalize |
| Google internal studies | Code quality is the strongest causal factor found; build latency has no single threshold; predictability matters | Single organization |
| [Steinmacher et al.](https://www.ime.usp.br/~gerosa/papers/08254320.pdf) | 57 barriers for OSS newcomers in 7 categories; local setup ranks first | Peer-reviewed |
| [Barik et al. / compiler-error studies](https://neverworkintheory.org/2021/09/02/compiler-error-messages-considered-unhelpful.html) | Developers spend 13–25% of task time reading errors (eye tracking) | Small lab studies |
| Interruption research (Mark) | Recovery from interruptions is slow; the often-quoted 23 minutes is contested | See the weak-evidence section |

Two cautions apply throughout: perception surveys can disagree with telemetry, and the AI-tooling literature is moving faster than the evidence.
