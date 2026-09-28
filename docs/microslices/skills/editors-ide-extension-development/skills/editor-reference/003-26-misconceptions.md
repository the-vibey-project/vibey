---
id: skill-26-misconceptions-8ceca638ab
purpose: 26 misconceptions
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-reference/SKILL.md
requires: ["skill-25-anti-patterns-22c488f5de"]
links: ["skill-27-numbers-c87f1623de"]
---

## §26. Misconceptions

| Misconception | Correction |
|---|---|
| Which editor you use determines your language support | ⚠️ **The language SERVER does** (§9 → `editor-vscode-architecture-and-the-protocol-layer`) |
| Vim is about memorizing shortcuts | ⚠️ **It's operator + motion/text-object grammar** (§3 → `editor-choosing-vim-neovim-and-emacs`) |
| Vim's `y` register survives a delete | ⚠️ **Use `"0` — the yank register** (§3 → `editor-choosing-vim-neovim-and-emacs`) |
| Neovim is Vim with a different name | ⚠️ **Built-in LSP, Tree-sitter, Lua, real async** (§4 → `editor-choosing-vim-neovim-and-emacs`, §24.2) |
| Extensions can manipulate VS Code's DOM | ⚠️ **Separate process. Use contributions or a webview** (§6 → `editor-vscode-architecture-and-the-protocol-layer`) |
| Monaco = embeddable VS Code | ⚠️ **The editor widget only; no workbench or extensions** (§6 → `editor-vscode-architecture-and-the-protocol-layer`) |
| VS Code extensions always run locally | ⚠️ **The host runs on the remote** (§8 → `editor-vscode-architecture-and-the-protocol-layer`) |
| Syntax highlighting needs regex grammars | ⚠️ **Tree-sitter parses structure** (§11 → `editor-vscode-architecture-and-the-protocol-layer`) |
| Tree-sitter can replace a language server | ⚠️ **Syntax vs semantics. You need both** (§11 → `editor-vscode-architecture-and-the-protocol-layer`) |
| LSP positions are byte offsets | ⚠️ **UTF-16 code units by default** (§9 → `editor-vscode-architecture-and-the-protocol-layer`) |
| A parser can assume valid input | ⚠️ **Code is invalid most of the time while typing** (§11 → `editor-vscode-architecture-and-the-protocol-layer`, §16 → `editor-vscode-extension-development`) |
| A text buffer can be a string | ⚠️ **O(n) edits; use rope/piece table/gap buffer** (§18 → `editor-internals-buffers-rendering-and-performance`) |
| Piece tables are exotic | ⚠️ **VS Code uses one** (§18 → `editor-internals-buffers-rendering-and-performance`) |
| Extensions can't slow startup much | ⚠️ **Activation events are the top complaint source** (§13 → `editor-vscode-extension-development`) |
| Cursor is a from-scratch editor | ⚠️ **A VS Code fork** (§24.2) |
| VS Code is losing to AI editors | ⚠️ **75.9% and rising; the entrants grew the field** (§24.2) |
| Copilot Chat is closed source | ⚠️ **MIT-licensed since 2025** (§24.1) |
| You must use Copilot's models in VS Code | ⚠️ **BYOK, including local models** (§24.1) |
| Pinning VS Code versions is harmless | ⚠️ **It pins your model access too** (§24.1) |

---
