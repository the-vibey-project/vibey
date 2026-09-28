---
id: skill-22-terminal-ui-programming-722196a390
purpose: 22 terminal ui programming
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-internals-buffers-rendering-and-performance/SKILL.md
requires: ["skill-21-the-jetbrains-platform-f753c8d65a"]
links: ["skill-23-editor-performance-4200f50b38"]
---

## §22. Terminal UI Programming

**⚠️ If you're building a terminal editor or TUI:**
**ANSI escape sequences, alternate screen buffer, raw mode, terminal capabilities
(terminfo), and ⚠️ the resize signal (SIGWINCH).**
**Libraries**: **ncurses, `crossterm`/`ratatui` (Rust), `bubbletea` (Go), `blessed`/`ink`
(Node), `prompt_toolkit`/`textual` (Python).**
**⚠️ The perennial gotchas**: ⚠️ **terminals vary enormously in capability; true-colour
support is inconsistent; wide (CJK) and zero-width characters break naive column
arithmetic; and mouse support requires explicit mode-setting and is inconsistently
implemented.**

---
