---
id: skill-29-quick-reference-8e6b503a97
purpose: 29 quick reference
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-reference/SKILL.md
requires: ["skill-28-resources-1a3b819107"]
links: ["skill-30-method-c6b59cac30"]
---

## §29. Quick Reference

### 29.1 Picker
| Question | Where |
|---|---|
| I'm stuck in vim | ⚠️ **`Esc` then `:q!`** (§3 → `editor-choosing-vim-neovim-and-emacs`) |
| How do I get good at vim? | ⚠️ **Learn operator+motion+text-object, not keys** (§3 → `editor-choosing-vim-neovim-and-emacs`) |
| Vim or Neovim? | ⚠️ **Neovim unless you need bare-server portability** (§4 → `editor-choosing-vim-neovim-and-emacs`, §24.2) |
| Language support is bad in my editor | ⚠️ **It's the language server, not the editor** (§9 → `editor-vscode-architecture-and-the-protocol-layer`) |
| Building tooling — which editor to target? | ⚠️ **Target the PROTOCOL** (§24.2) |
| Syntax highlighting or structural search | ⚠️ **Tree-sitter / ast-grep** (§11 → `editor-vscode-architecture-and-the-protocol-layer`) |
| Cross-project semantics | ⚠️ **LSP** (§9 → `editor-vscode-architecture-and-the-protocol-layer`) |
| VS Code is slow to start | ⚠️ **Show Running Extensions; check activation** (§13 → `editor-vscode-extension-development`, §23 → `editor-internals-buffers-rendering-and-performance`) |
| Extension needs custom UI | ⚠️ **Native contributions first; webview last** (§15 → `editor-vscode-extension-development`) |
| Simple language feature, one language | ⚠️ **In-process provider** (§14 → `editor-vscode-extension-development`) |
| Heavy analysis or non-Node toolchain | ⚠️ **Write a language server** (§16 → `editor-vscode-extension-development`) |
| Extension breaks over SSH | ⚠️ **Check `extensionKind` and path assumptions** (§8 → `editor-vscode-architecture-and-the-protocol-layer`) |
| Building an editor — buffer choice? | ⚠️ **Rope or piece table; check line lookup cost** (§18 → `editor-internals-buffers-rendering-and-performance`) |
| Want a different model in VS Code | ⚠️ **BYOK** (§24.1) |

### 29.2 Extension checklist
- [ ] ⚠️ **Narrow activation events; startup cost measured** (§13 → `editor-vscode-extension-development`)
- [ ] ⚠️ **Every disposable pushed to `context.subscriptions`** (§12 → `editor-vscode-extension-development`)
- [ ] Logic separated from the `vscode` API for testability (§17 → `editor-vscode-extension-development`)
- [ ] ⚠️ **Works when the extension host is remote** (§8 → `editor-vscode-architecture-and-the-protocol-layer`)
- [ ] `WorkspaceEdit` for file changes, not direct writes (§14 → `editor-vscode-extension-development`)
- [ ] Webview: CSP, nonce, `asWebviewUri`, theme variables (§15 → `editor-vscode-extension-development`)
- [ ] ⚠️ **Cancellation tokens honoured; requests debounced** (§9 → `editor-vscode-architecture-and-the-protocol-layer`)
- [ ] `engines.vscode` accurate; `.vscodeignore` trimmed (§12 → `editor-vscode-extension-development`, §17 → `editor-vscode-extension-development`)
- [ ] ⚠️ **Published to Open VSX as well, if reach matters** (§17 → `editor-vscode-extension-development`)

---
