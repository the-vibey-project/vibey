---
id: skill-30-method-c6b59cac30
purpose: 30 method
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-reference/SKILL.md
requires: ["skill-29-quick-reference-8e6b503a97"]
links: []
---

## §30. Method

**§1–§23 → `editor-choosing-vim-neovim-and-emacs`, `editor-vscode-architecture-and-the-protocol-layer`, `editor-vscode-extension-development`, `editor-internals-buffers-rendering-and-performance` rests on stable material** — **modal editing, the VS Code process model, the LSP
and DAP specifications, Tree-sitter, buffer data structures and rendering.** ⚠️ **The
protocols have been stable for years and the buffer structures are decades old; none of it
needed verification.**

**Two searches were run in August 2026**, on **the AI/agent layer in VS Code** and **the
editor landscape** — ⚠️ **the first because it introduced genuinely new extension APIs, the
second because the competitive picture changed enough to affect what you target.**

**Confidence.** **High** in §9 → `editor-vscode-architecture-and-the-protocol-layer` and §11 → `editor-vscode-architecture-and-the-protocol-layer`, and the protocol framing in the header is the
argument I'd most defend: ⚠️ **the shift from editors × languages to editors + languages is
the structural change that explains why new editors are viable, why editor choice matters
less, and why tooling should target protocols.** **One 2026 analysis states it directly —
hooking into the standards is cheaper than building a new editor — and Helix, Zed and
Neovim all demonstrate it.**

**High** in §12–§17 → `editor-vscode-extension-development`'s extension mechanics and §18 → `editor-internals-buffers-rendering-and-performance`'s buffer structures, which come from
primary documentation and are long-stable.

**High** in §24.1's facts, which trace to GitHub's own changelog and VS Code's blog:
⚠️ **the MIT open-sourcing of Copilot Chat, the BYOK provider list and its exclusion of
code completions, the Language Model Chat Provider API, and the lockstep versioning
constraint are all from primary sources.** **The lockstep point is from the repository's
own README and is the one I'd most want a reader on a pinned VS Code version to see.**

**Moderate-to-high** in §24.2's numbers. ⚠️ **The Stack Overflow figures (VS Code 75.9%,
IntelliJ 27.1%, Vim 24.3%, Neovim 14%) and the AI-native debut percentages come from
secondary reporting of the survey rather than from the survey directly in my results, and
different sources cite 2024 vs 2025 waves — I've dated them and would verify against
Stack Overflow's own publication before quoting.** **⚠️ The Neovim 0.12 and Vim 9.2 release
details come from an aggregator and are marked as reported.**

⚠️ **ACP is deliberately flagged as early and reported rather than established.** **The
adoption claims (JetBrains, Gemini CLI, Copilot CLI, 25+ agents, shared registry) come
from a single tech-analysis source.** **The "LSP of AI coding" framing is plausible — the
M×N problem shape is identical — but a protocol roughly a year old is not yet a standard,
and I'd rather say that than repeat the marketing.** ⚠️ **Sourcing caution generally: much
of the editor-comparison material comes from review sites and tool directories with
affiliate relationships; I anchored on primary changelogs and specifications wherever the
claim mattered.**
