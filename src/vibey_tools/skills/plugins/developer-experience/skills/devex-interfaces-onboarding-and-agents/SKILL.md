---
name: devex-interfaces-onboarding-and-agents
description: "Use when building a web UI, TUI or dashboard for developers; making a terminal tool accessible to screen-reader users; onboarding new contributors or maintainers; writing CONTRIBUTING.md and good-first-issues; building golden paths; or making a repository usable by coding agents: AGENTS.md, llms.txt, MCP server tool count and token budgets, deterministic CLI output, agent guard rails. Triggers on TUI accessibility, keyboard-first, onboarding time to first hello world, Steinmacher barriers, golden path, AGENTS.md, llms.txt, MCP tool design. Companion to the other developer-experience skills."
---

# Developer Experience: Interfaces, Onboarding, and AI-Agent Ergonomics

> **Part 4 of 9** of the *Developer Experience Blueprint* (plugin `developer-experience`), covering: Interfaces: web UI, TUI, accessibility; Onboarding and open-source contribution; AI-agent ergonomics. Sibling skills: `devex-principles-and-feedback-loops`, `devex-cli-and-errors`, `devex-api-sdk-and-docs`, `devex-surface-placement`, `devex-editor-and-desktop-surfaces`, `devex-mobile-and-web-surfaces`, `devex-non-developers-and-visual-design`, `devex-reference`. A reference into a sibling is written *Section name → `skill`*.
>
> **Currency:** the blueprint is dated Oct 23, 2026; its evidence base and the AI-tooling claims age fastest, so re-check those first.
>
> Evidence grades used throughout: **A** = peer-reviewed or large study, **B** = credible practitioner or single study, **C** = vendor or opinion. Thin evidence is flagged where it occurs, and collected under *Where the evidence is weak or conflicting* in `devex-reference`.

## Interfaces: web UI, TUI, accessibility

- **Show state and next action.** Every screen says what is running, what failed and what to do; long operations show progress and stay cancelable.
- **Keyboard first.** Every action reachable from the keyboard, a command palette, visible shortcuts, and no focus traps.
- **Respect the terminal.** A TUI must degrade to plain output when piped, honor `NO_COLOR`, and never leave the terminal in a broken mode after a crash.
- **Make logs and diffs scannable.** Monospace, stable columns, copy buttons, deep links to a failing step.
- **Accessibility is a requirement, not polish.** Meet WCAG contrast and focus rules, label controls, and do not rely on color alone. For command lines, research presented at CHI 2021 found that unstructured text output is the core problem for screen-reader users, so structured, consistently ordered output (and a `--plain` mode) helps. I verified this finding only from the abstract and a secondary summary.
- **Dark mode and density options** for tools used all day.
- **Same vocabulary everywhere:** the UI, CLI, API and docs use identical names for the same thing.

## Onboarding and open-source contribution

The [Steinmacher barrier model](https://www.ime.usp.br/~gerosa/papers/08254320.pdf) lists 57 barriers in 7 categories; setting up the local environment ranks as the top one, and the tool FLOSScoach was built to guide newcomers through them.

- **Time to first hello world** is the headline onboarding metric; measure it with a fresh machine and a stopwatch every quarter.
- **CONTRIBUTING.md** states how to set up, test, and submit, how long review takes, and what a good pull request looks like.
- **Good first issues** are scoped, reproducible and have a named mentor; studies of them find that mentoring is the key driver of whether newcomers stay.
- **Reproducible environments** (dev containers, Devbox or Nix) remove the setup barrier.
- **Golden paths.** Platform teams offer one supported route for common tasks to cut cognitive load; make it the easiest route, not the mandatory one.
- **Respond fast.** Acknowledge first-time contributors quickly, even if the full review takes longer.
- **Ramp-up measurement.** Google tracks how long new engineers take to reach their first change; copy the idea with first-commit and tenth-commit dates.

## AI-agent ergonomics

Coding agents now read your repository, so treat them as a second class of user. Evidence is practitioner-level and changing fast.

- **AGENTS.md** at the repo root: build and test commands, code style, project layout, and gotchas, kept short. Adoption counts conflict between sources (over 20,000 versus over 60,000 repositories), so treat both as rough.
- **llms.txt** for docs sites: a curated markdown index of key pages (see [Cloudinary's](https://cloudinary.com/documentation/llms.txt) as an example, and append `.md` to page URLs where you can serve markdown). No confirmed search-ranking effect, but coding tools do read it.
- **MCP servers:** every tool definition costs context tokens. Keep the tool count low, name tools by the job, return paginated results with a token budget, and consider code-execution patterns for heavy data work. Compact formats such as YAML can cost fewer tokens than JSON.
- **Deterministic interfaces:** JSON output, stable exit codes and no prompts let agents run your CLI safely.
- **Guard rails:** dry-run modes, scoped credentials and readable audit logs matter more when the caller is automated.
- **Do not assume speedups.** The METR trial found experienced developers 19% slower with AI in one narrow setting, so measure the effect on your own team.
