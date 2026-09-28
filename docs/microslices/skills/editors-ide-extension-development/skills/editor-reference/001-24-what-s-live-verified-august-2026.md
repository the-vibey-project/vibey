---
id: skill-24-what-s-live-verified-august-2026-101a9c6926
purpose: 24 what s live verified august 2026
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-reference/SKILL.md
requires: []
links: ["skill-25-anti-patterns-22c488f5de"]
---

## §24. What's Live — verified August 2026

### 24.1 ⚠️ The AI/agent layer became part of the editor platform
**⚠️ For extension authors this is the most consequential API change in years: the model
became a resource the editor exposes, not a feature one vendor owns.**

- **⚠️ Microsoft open-sourced the GitHub Copilot Chat extension under the MIT license**
  (announced at Build 2025, repository `microsoft/vscode-copilot-chat`), **exposing the
  full implementation of agent mode, what contextual data is sent to models, the system
  prompt design, and telemetry mechanisms.** ⚠️ **The stated rationale is worth noting:
  advances in LLMs reduced the value of proprietary prompting, keeping prompts secret is
  impractical against community reverse-engineering, and openness was judged better for
  security given increased targeting of developer tools.**
- **⚠️ Bring-your-own-key (BYOK) is now a first-class capability.** **Copilot Business and
  Enterprise users can use their own API keys for providers including Anthropic, Gemini,
  OpenAI, OpenRouter and Azure, plus local models via Ollama and Foundry Local
  (changelog dated 22 April 2026).** ⚠️ **BYOK models work anywhere in VS Code Chat
  including agent mode and custom agents; usage is billed by the provider and does NOT
  count against Copilot quotas; and code completions are excluded — they stay on Copilot
  infrastructure.** **⚠️ BYOK was subsequently extended to air-gapped environments.**
- **⚠️ The extension-facing surface is the Language Model Chat Provider API**, ⚠️ **which
  means an extension can CONTRIBUTE models to the editor's picker** — **this is what turns
  the model layer into an ecosystem rather than a product.**
- **⚠️ Agent infrastructure is now editor-level**: **an Agents window shipped to Stable as
  preview in May 2026; sessions hold conversation, workspace, changes and execution state
  so work can be paused and resumed; ⚠️ and worktree support lets Copilot, Claude or Codex
  sessions each work in an isolated copy of the repository.** **MCP servers are the
  documented way to extend agents with external tools.**

> **⚠️ GOTCHA — a versioning constraint that catches teams on locked-down VS Code
> versions.** ⚠️ **Copilot Chat releases in LOCKSTEP with VS Code because of deep UI
> integration: every new Copilot Chat version is only compatible with the newest VS Code
> release, and only the latest Copilot Chat gets the latest models** — **because even minor
> model upgrades require prompt changes in the extension.** **⚠️ If your organization pins
> VS Code versions, you are also pinning model access.**

**⚠️ And note the economics changed underneath** (see a GitHub/Jira reference §26.2):
⚠️ **Copilot moved from flat premium-request units to token-based AI Credits on 1 June
2026**, **which is why BYOK matters — it routes heavy usage to a provider you bill
directly.**

### 24.2 ⚠️ The editor landscape: dominance plus genuine new entrants
**⚠️ VS Code remains dominant and the surrounding field got materially more interesting.**

- **⚠️ Stack Overflow's 2025 survey (49,000+ respondents, 177 countries) put VS Code at
  75.9%**, **up from 73.6% in 2024** — ⚠️ **more than triple its nearest competitor.**
  **IntelliJ IDEA at 27.1%; ⚠️ among Java developers specifically, IntelliJ reportedly rose
  from 71% to 84%.** **⚠️ Terminal editors remain substantial: Vim 24.3%, Neovim 14%.**
- **⚠️ AI-native editors posted the fastest debuts recorded**: **Cursor entering at 17.9%,
  Claude Code at 9.7%, Zed at 7.3%, Windsurf at 4.9%.** ⚠️ **Cursor is a VS Code fork,
  which is itself the story — the extension ecosystem and the Monaco/workbench foundation
  made forking viable.**
- **⚠️ Zed is the substantive non-Electron entrant**: **built in Rust by Nathan Sobo
  (Atom co-creator) and Max Brunsfeld (Tree-sitter's creator), rendered on the GPU via a
  custom framework, GPL-3.0, with full LSP support for 80+ languages.** ⚠️ **Windows and
  Linux support reportedly matured in early 2026, which was its main practical gap.**
- **⚠️ Neovim 0.12 (reported March 2026) added a built-in plugin manager plus LSP and UI
  upgrades** — ⚠️ **continuing the pattern of absorbing into core what previously required
  plugins.** **Vim 9.2 (reported February 2026) added fuzzy completion, Wayland support
  and XDG config.**
- **⚠️ JetBrains discontinued Fleet in December 2025 after 3+ years in preview**, **reported
  replaced by an agent-first product; treat the successor's details as unsettled.**

> **⚠️ GOTCHA — the strategic point, and it's the §9 → `editor-vscode-architecture-and-the-protocol-layer`/§11 → `editor-vscode-architecture-and-the-protocol-layer` thesis confirmed.** ⚠️ **New
> editors are viable within a year or two precisely BECAUSE LSP and Tree-sitter exist.**
> **Helix and Zed baked both in from day one rather than reimplementing language support;
> Neovim shipped an LSP client in core from 0.5.** **⚠️ One 2026 analysis puts it directly:
> hooking into the standards is far cheaper than building a new editor.**
> **⚠️ The corollary for anyone building tooling: target the PROTOCOL, not an editor.**
> **A language server or a Tree-sitter grammar works everywhere; a VS Code extension works
> in VS Code and its forks.**

**⚠️ One protocol to watch, flagged as early**: **the Agent Client Protocol (ACP), debuted
by Zed in August 2025, is reported adopted during 2026 by JetBrains across IntelliJ and
PyCharm, by Google's Gemini CLI, and by GitHub's Copilot CLI, with a shared agent
registry and 25+ agents reported speaking it.** ⚠️ **It is being described as "the LSP of
AI coding," which is a strong claim from a young protocol** — **the LSP analogy is
plausible given the identical M×N problem shape, and I'd treat the adoption numbers as
reported rather than verified.**

---
