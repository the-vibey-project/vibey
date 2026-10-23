---
id: skill-interfaces-web-ui-tui-accessibility-1010febab1
purpose: interfaces web ui tui accessibility
source: src/vibey_tools/skills/plugins/developer-experience/skills/devex-interfaces-onboarding-and-agents/SKILL.md
requires: []
links: ["skill-onboarding-and-open-source-contribution-8bad7cb779"]
---

## Interfaces: web UI, TUI, accessibility

- **Show state and next action.** Every screen says what is running, what failed and what to do; long operations show progress and stay cancelable.
- **Keyboard first.** Every action reachable from the keyboard, a command palette, visible shortcuts, and no focus traps.
- **Respect the terminal.** A TUI must degrade to plain output when piped, honor `NO_COLOR`, and never leave the terminal in a broken mode after a crash.
- **Make logs and diffs scannable.** Monospace, stable columns, copy buttons, deep links to a failing step.
- **Accessibility is a requirement, not polish.** Meet WCAG contrast and focus rules, label controls, and do not rely on color alone. For command lines, research presented at CHI 2021 found that unstructured text output is the core problem for screen-reader users, so structured, consistently ordered output (and a `--plain` mode) helps. I verified this finding only from the abstract and a secondary summary.
- **Dark mode and density options** for tools used all day.
- **Same vocabulary everywhere:** the UI, CLI, API and docs use identical names for the same thing.
