---
id: skill-14-api-surfaces-9a67059403
purpose: 14 api surfaces
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-vscode-extension-development/SKILL.md
requires: ["skill-13-contribution-points-and-activation-409a216508"]
links: ["skill-15-webviews-0948050610"]
---

## §14. API Surfaces

```
window      ⚠️ messages, quick pick, input box, status bar, output channel,
            terminals, editors, webviews, progress
workspace   ⚠️ folders, file system, configuration, text documents,
            FILE SYSTEM WATCHERS, edits
languages   ⚠️ register providers: completion, hover, definition, code
            actions, formatting, diagnostics. ⚠️ Use these instead of an
            LSP server for simple, single-language, in-process features
commands    register and execute (⚠️ including built-in commands)
debug · tasks · extensions · env · authentication · lm (§24.1)
```
**⚠️ Choosing between in-process providers and a language server** (§16): ⚠️ **in-process
is simpler and locks you to VS Code and to Node; an LSP server is more work and runs
anywhere, in any language, in its own process.** **⚠️ If the analysis is heavy or the
language has an existing toolchain in another language, write a server.**
**⚠️ `WorkspaceEdit`** is how you make multi-file changes atomically with undo support —
⚠️ **don't write files directly when a WorkspaceEdit will do, because direct writes break
undo and don't participate in refactoring previews.**

---
