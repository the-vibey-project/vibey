---
id: skill-principles-639aa30050
purpose: principles
source: src/vibey_tools/skills/plugins/developer-experience/skills/devex-principles-and-feedback-loops/SKILL.md
requires: []
links: ["skill-evidence-base-339b8b7252"]
---

## Principles

These ten rules are the synthesis; each ends with an evidence grade (A = peer-reviewed or large study, B = credible practitioner or single study, C = vendor or opinion).

1. **Shorten and protect feedback loops.** Build, test, lint and review latency decide how often developers stay in flow. Grade B: [DevEx (ACM Queue)](https://queue.acm.org/detail.cfm?id=3595878) names feedback loops, cognitive load and flow state as the three core dimensions.
2. **Make behavior predictable.** Predictable build times and stable tests matter more than a magic speed threshold. Grade B (Google internal studies; [DX newsletter on build times](https://newsletter.getdx.com/p/build-times-and-developer-productivity)).
3. **Put the next step in every output.** Help text, errors and docs all say what to do next, with a runnable example. Grade B (CLI guidelines, Rust diagnostics).
4. **Be consistent before being clever.** Same names, same flags, same placement across the whole surface. Grade A for APIs (Myers & Stylos).
5. **Choose safe defaults; make danger explicit.** Dry-run, confirmation and non-interactive modes. Grade C (practitioner consensus).
6. **Separate human output from machine output.** Data to stdout, messages to stderr, stable JSON on request, meaningful exit codes. Grade B.
7. **Document by purpose.** Tutorials, how-tos, reference and explanation are different jobs. Grade C (Diátaxis; read only through secondary sources).
8. **Make local setup one command.** Environment setup is the top barrier for newcomers. Grade A ([Steinmacher et al. barrier model](https://www.ime.usp.br/~gerosa/papers/08254320.pdf)).
9. **Design for agents too.** A root instruction file, structured output and few, well-named tools. Grade C (new, mostly practitioner evidence).
10. **Measure perception and workflow together.** Survey developers and pair it with system data; pick one North Star per team. Grade B (DevEx; SPACE).
